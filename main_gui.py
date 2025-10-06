import tkinter as tk
from tkinter import filedialog, ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

class SalesDataVisualizer:
    """
    Aplicación GUI que carga datos (CSV/XLSX), valida 'fecha' y 'ventas',
    y genera un gráfico embebido (Línea o Barras).
    """
    
    REQUIRED_COLUMNS = {"fecha", "ventas"}
    
    def __init__(self, master):
        self.master = master
        master.title("Visualizador de Datos de Ventas - Académico")
        master.geometry("1000x700")

        self.dataframe = None
        self.file_path = None
        self.chart_canvas = None

        # --- ESTRUCTURA DE LA GUI (ETAPA 1) ---
        
        # Frame de Controles (Botón, Archivo, Selector Gráfico)
        self.control_frame = ttk.Frame(master, padding="10")
        self.control_frame.grid(row=0, column=0, sticky="ew")
        
        self.load_button = ttk.Button(
            self.control_frame, 
            text="Cargar Archivo (CSV/XLSX)", 
            command=self.load_file
        )
        self.load_button.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.file_label = ttk.Label(
            self.control_frame, 
            text="Archivo: Ninguno cargado", 
            foreground="blue"
        )
        self.file_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # Selector de Tipo de Gráfico
        self.chart_type = tk.StringVar(value='linea')
        ttk.Label(self.control_frame, text="Tipo de Gráfico:").grid(row=0, column=2, padx=(20, 5), pady=5)
        self.radio_line = ttk.Radiobutton(self.control_frame, text="Líneas", variable=self.chart_type, value='linea', command=self._replot_if_data_loaded)
        self.radio_bar = ttk.Radiobutton(self.control_frame, text="Barras", variable=self.chart_type, value='barras', command=self._replot_if_data_loaded)
        self.radio_line.grid(row=0, column=3, padx=5, pady=5)
        self.radio_bar.grid(row=0, column=4, padx=5, pady=5)


        # Mensajes de Estado/Error
        self.status_label = ttk.Label(
            master, 
            text="Estado: Listo.", 
            wraplength=980, 
            justify=tk.LEFT,
            background="#f0f0f0",
            relief=tk.SUNKEN
        )
        self.status_label.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Espacio para el Gráfico
        self.graph_frame = ttk.Frame(master, relief=tk.RIDGE, borderwidth=2)
        self.graph_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        
        self.placeholder_label = ttk.Label(
            self.graph_frame, 
            text="Aquí se mostrará el Gráfico de Ventas vs. Fecha",
            anchor="center"
        )
        self.placeholder_label.pack(expand=True, fill="both", padx=20, pady=20)

        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(2, weight=1)
        self.control_frame.grid_columnconfigure(1, weight=1)

    # --- FUNCIONALIDAD DE CARGA Y VALIDACIÓN (ETAPAS 2 & 3) ---

    def load_file(self):
        """Maneja el diálogo de selección de archivos y la carga."""
        self.clear_chart() 
        
        f_types = [
            ('Archivos de Datos', '*.csv *.xlsx *.xls'),
            ('Archivos CSV', '*.csv'), 
            ('Archivos Excel', '*.xlsx *.xls')
        ]
        
        # Diálogo de selección (tkinter.filedialog)
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de datos de ventas",
            filetypes=f_types
        )
        
        if not file_path:
            self.update_status("Carga cancelada.", is_error=False)
            return

        self.file_path = file_path
        self.file_label.config(text=f"Archivo: {file_path.split('/')[-1]}")
        self.update_status(f"Cargando {file_path.split('/')[-1]}...")
        self._read_data_with_pandas()

    def _read_data_with_pandas(self):
        """Detecta la extensión y lee el archivo, incluyendo manejo de errores (ETAPA 5)."""
        ext = self.file_path.split('.')[-1].lower()
        
        try:
            # Detección automática de formato (CSV/XLSX)
            if ext == 'csv':
                try:
                    df = pd.read_csv(self.file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(self.file_path, encoding='latin1')
            elif ext in ('xlsx', 'xls'):
                df = pd.read_excel(self.file_path)
            else:
                raise ValueError(f"Formato de archivo no soportado: .{ext}")
            
            self.dataframe = df
            self._validate_and_process_data()

        except Exception as e:
            self.update_status(f"ERROR I/O o Parser: {e}", is_error=True)
            self.dataframe = None

    def _validate_and_process_data(self):
        """Valida la presencia de columnas, formato de fecha (ISO 8601) y tipo numérico."""
        df = self.dataframe
        
        # Validación de columnas
        df.columns = df.columns.str.lower()
        if not self.REQUIRED_COLUMNS.issubset(df.columns):
            missing = self.REQUIRED_COLUMNS - set(df.columns)
            self.update_status(
                f"ERROR: Faltan columnas obligatorias: {missing}.", 
                is_error=True
            )
            self.dataframe = None
            return

        try:
            # 1. Validación y Conversión de "ventas" (Numérico)
            df['ventas'] = pd.to_numeric(df['ventas'], errors='coerce')
            if df['ventas'].isnull().sum() > 0.5 * len(df):
                 raise TypeError("La columna 'ventas' no es mayoritariamente numérica.")

            # 2. Validación y Conversión de "fecha" (ISO 8601 "YYYY-MM-DD")
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', format='%Y-%m-%d')
            if df['fecha'].isnull().sum() > 0.5 * len(df):
                raise TypeError("La columna 'fecha' no está en el formato 'YYYY-MM-DD' o similar.")
            
            # Limpieza y preparación
            df_cleaned = df.dropna(subset=['fecha', 'ventas']).copy()
            if df_cleaned.empty:
                raise ValueError("No quedan datos válidos de fecha/ventas después de la limpieza.")
            
            self.dataframe = df_cleaned
            self.update_status("DATOS CARGADOS Y VALIDADOS exitosamente. Generando gráfico...", is_error=False)
            
            self.plot_data() 
            
        except (TypeError, ValueError) as e:
            self.update_status(f"ERROR de Datos/Formato: {e}", is_error=True)
            self.dataframe = None
        except Exception as e:
            self.update_status(f"ERROR Desconocido durante la validación: {e}", is_error=True)
            self.dataframe = None

    # --- GENERACIÓN DE GRÁFICOS (ETAPA 4) ---

    def _replot_if_data_loaded(self):
        """Regenera el gráfico al cambiar el tipo."""
        if self.dataframe is not None and not self.dataframe.empty:
            self.plot_data()

    def plot_data(self):
        """Genera y embebe el gráfico de ventas vs. fecha."""
        df = self.dataframe

        self.clear_chart() 
        self.placeholder_label.pack_forget()

        # Agrupar las ventas para que cada fecha tenga un único punto de datos
        df_plot = df.groupby('fecha')['ventas'].sum().reset_index()
        
        # Configuración de Matplotlib Figure
        fig = Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)

        # Generación del Gráfico (Líneas o Barras)
        chart_type = self.chart_type.get()
        
        if chart_type == 'linea':
            ax.plot(df_plot['fecha'], df_plot['ventas'], marker='o', linestyle='-', color='blue')
        elif chart_type == 'barras':
            dates = df_plot['fecha'].dt.strftime('%Y-%m-%d')
            ax.bar(dates, df_plot['ventas'], color='skyblue')
            # Rotar etiquetas para mejorar legibilidad si hay muchos puntos
            if len(df_plot) > 15:
                fig.autofmt_xdate(rotation=45) 

        # Personalización
        ax.set_title(f"Ventas Diarias vs. Fecha ({chart_type.capitalize()})", fontsize=14)
        ax.set_xlabel("Fecha", fontsize=12)
        ax.set_ylabel("Ventas Totales", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        fig.tight_layout()

        # Embeber el Gráfico
        self.chart_canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        self.chart_canvas_widget = self.chart_canvas.get_tk_widget()
        self.chart_canvas_widget.pack(fill=tk.BOTH, expand=True)

    # --- MANEJO DE ERRORES Y PULIDO (ETAPA 5) ---

    def update_status(self, message, is_error=False):
        """Actualiza el mensaje de estado con color indicando éxito o error."""
        color = "red" if is_error else "green"
        self.status_label.config(text=f"Estado: {message}", foreground=color)
        
    def clear_chart(self):
        """Limpia el área del gráfico."""
        if self.chart_canvas:
            self.chart_canvas_widget.destroy()
            self.chart_canvas = None
            
        # Vuelve a mostrar el placeholder si no hay datos
        if self.dataframe is None or self.dataframe.empty:
             self.placeholder_label.pack(expand=True, fill="both", padx=20, pady=20)


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = SalesDataVisualizer(root)
        root.mainloop()
    except Exception as e:
        # Esto captura errores fatales fuera de los try/excepts de la aplicación
        print(f"La aplicación falló al iniciar: {e}")
