Kankai Pro - Gestor de Tareas Kanban con Streamlit
"Kankai Pro" es una aplicación de tablero Kanban interactiva y visual, construida completamente con Python y la librería Streamlit. Permite a los usuarios gestionar sus tareas de manera eficiente a través de diferentes estados, visualizar su progreso y obtener sugerencias sobre cómo abordar las tareas pendientes.

Esta versión es una adaptación de una aplicación originalmente desarrollada con Flask y una interfaz HTML/JavaScript.

Características Principales
Tablero Kanban Visual: Organiza las tareas en tres columnas: "Por Hacer", "En Progreso" y "Finalizado".

Gestión de Tareas:

Añade nuevas tareas especificando nombre, tiempo estimado y nivel de dificultad.

Mueve las tareas entre los diferentes estados con simples clics de botón.

Elimina tareas una vez que han sido completadas.

Análisis de Progreso:

Un gráfico de dona muestra visualmente el porcentaje de tareas completadas frente a las pendientes.

Una métrica clara indica el número total de tareas finalizadas.

Optimización de Tareas: Con un solo clic, la aplicación sugiere un orden óptimo para abordar las tareas pendientes, priorizando por dificultad (de menor a mayor) y luego por tiempo estimado (del más corto al más largo).

Exportación a Excel: Genera y descarga un reporte completo de todas las tareas y un gráfico del progreso general en un archivo .xlsx.

Estructura del Proyecto
app.py: El script principal de Python que contiene toda la lógica de la aplicación y la definición de la interfaz de usuario con Streamlit.

requirements.txt: El archivo que lista todas las dependencias de Python necesarias para ejecutar el proyecto.

Cómo Ejecutar la Aplicación Localmente
Sigue estos pasos para poner en marcha la aplicación en tu máquina local.

Clonar el Repositorio:

git clone <URL-de-tu-repositorio-en-GitHub>
cd <nombre-del-repositorio>

Crear y Activar un Entorno Virtual (Recomendado):
Esto aísla las dependencias de tu proyecto.

# Crear el entorno
python3 -m venv venv

# Activar en macOS/Linux
source venv/bin/activate

# Activar en Windows
.\venv\Scripts\activate

Instalar las Dependencias:
El archivo requirements.txt contiene todas las librerías necesarias.

pip install -r requirements.txt

Ejecutar la Aplicación Streamlit:
Una vez instaladas las dependencias, ejecuta el siguiente comando en tu terminal:

streamlit run app.py

Streamlit iniciará un servidor local y abrirá la aplicación automáticamente en tu navegador web.

Despliegue en Streamlit Community Cloud
Esta aplicación está lista para ser desplegada gratuitamente en la plataforma de Streamlit.

Sube tu código a un repositorio público en GitHub. Asegúrate de que los archivos app.py y requirements.txt estén en la raíz del repositorio.

Regístrate en Streamlit Community Cloud usando tu cuenta de GitHub.

Desplegar la aplicación:

Desde tu panel de control, haz clic en "New app".

Selecciona el repositorio de GitHub que acabas de subir.

Asegúrate de que la rama (main o master) y el archivo principal (app.py) estén correctamente seleccionados.

Haz clic en "Deploy!".

Streamlit se encargará del resto, instalando las dependencias y poniendo tu aplicación en línea para que puedas compartirla con una URL pública.
