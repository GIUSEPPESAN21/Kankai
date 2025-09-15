# -*- coding: utf-8 -*-
"""
Aplicación de Tablero Kanban "Kankai" con Streamlit.

Esta es una adaptación de una aplicación Kanban construida con Flask y HTML/JavaScript.
Proporciona una interfaz visual e interactiva para la gestión de tareas, incluyendo:
- Creación y eliminación de tareas.
- Movimiento de tareas entre estados (drag-and-drop implícito).
- Visualización del progreso general con un gráfico.
- Sugerencias de optimización para el orden de las tareas.
- Exportación de datos a un archivo Excel.
"""
import streamlit as st
import pandas as pd
import time
import math
from io import BytesIO
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.utils.dataframe import dataframe_to_rows

# --- Lógica de Negocio y Manejo de Datos ---

class TaskManager:
    """
    Clase para manejar la lógica de las tareas del tablero Kanban.
    """
    def __init__(self):
        # Utiliza st.session_state para mantener los datos.
        if 'tasks_df' not in st.session_state:
            st.session_state.tasks_df = pd.DataFrame([
                {'id': 'task-1', 'name': 'Diseñar Prototipo Alfa', 'estimatedTimeMinutes': 480, 'difficulty': '2', 'status': 'todo'},
                {'id': 'task-2', 'name': 'Investigación de Mercado UX', 'estimatedTimeMinutes': 720, 'difficulty': '3', 'status': 'todo'},
                {'id': 'task-3', 'name': 'Reunión Kick-off Proyecto K', 'estimatedTimeMinutes': 60, 'difficulty': '1', 'status': 'inprogress'},
                {'id': 'task-4', 'name': 'Configurar Entorno Dev', 'estimatedTimeMinutes': 240, 'difficulty': '1', 'status': 'done'},
            ])
        if 'next_task_id' not in st.session_state:
            st.session_state.next_task_id = 5

        self.difficulty_map = {'1': 'Baja', '2': 'Media', '3': 'Alta'}
        self.difficulty_sort_order = {'1': 1, '2': 2, '3': 3}

    def get_tasks(self):
        return st.session_state.tasks_df

    def add_task(self, name, estimated_minutes, difficulty):
        name = name.strip()
        if not name or estimated_minutes <= 0:
            st.error("El nombre no puede estar vacío y el tiempo debe ser positivo.")
            return

        new_id = f"task-{st.session_state.next_task_id}"
        new_task = pd.DataFrame([{
            'id': new_id,
            'name': name,
            'estimatedTimeMinutes': estimated_minutes,
            'difficulty': difficulty,
            'status': 'todo'
        }])
        st.session_state.tasks_df = pd.concat([st.session_state.tasks_df, new_task], ignore_index=True)
        st.session_state.next_task_id += 1
        st.toast(f"Tarea '{name}' creada.", icon="📝")
        # Aquí se podrían integrar notificaciones de Twilio si se configuran los secrets.

    def update_task_status(self, task_id, new_status):
        task_idx = st.session_state.tasks_df[st.session_state.tasks_df['id'] == task_id].index
        if not task_idx.empty:
            st.session_state.tasks_df.loc[task_idx, 'status'] = new_status
            task_name = st.session_state.tasks_df.loc[task_idx[0], 'name']
            st.toast(f"Tarea '{task_name}' movida a '{new_status}'.", icon="🔄")

    def delete_task(self, task_id):
        task_name = st.session_state.tasks_df[st.session_state.tasks_df['id'] == task_id].iloc[0]['name']
        st.session_state.tasks_df = st.session_state.tasks_df[st.session_state.tasks_df['id'] != task_id]
        st.toast(f"Tarea '{task_name}' eliminada.", icon="🗑️")

    def get_optimization_suggestion(self):
        tasks_to_optimize = st.session_state.tasks_df[
            st.session_state.tasks_df['status'].isin(['todo', 'inprogress'])
        ].copy()
        
        # Crear una columna temporal para ordenar por dificultad
        tasks_to_optimize['difficulty_order'] = tasks_to_optimize['difficulty'].map(self.difficulty_sort_order)
        
        # Ordenar por dificultad y luego por tiempo estimado
        optimized = tasks_to_optimize.sort_values(
            by=['difficulty_order', 'estimatedTimeMinutes'],
            ascending=[True, True]
        )
        return optimized

    def get_progress_summary(self):
        total_tasks = len(st.session_state.tasks_df)
        if total_tasks == 0:
            return {'done': 0, 'pending': 0, 'total': 0, 'percentage': 0}
        
        done_tasks = len(st.session_state.tasks_df[st.session_state.tasks_df['status'] == 'done'])
        pending_tasks = total_tasks - done_tasks
        percentage = round((done_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0
        
        return {
            'done': done_tasks,
            'pending': pending_tasks,
            'total': total_tasks,
            'percentage': percentage
        }

# --- Funciones Auxiliares y de UI ---

def format_minutes_to_hm(minutes):
    if pd.isna(minutes) or minutes < 0:
        return "N/A"
    h = int(minutes // 60)
    m = int(minutes % 60)
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    elif h > 0:
        return f"{h}h"
    else:
        return f"{m}m"

def create_progress_chart(summary):
    if summary['total'] == 0:
        return None

    labels = ['Finalizadas', 'Pendientes']
    sizes = [summary['done'], summary['pending']]
    colors = ['#10b981', '#f59e0b']
    
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
           colors=colors, wedgeprops=dict(width=0.4, edgecolor='w'))
    ax.axis('equal')  # Asegura que el pie sea un círculo.
    return fig

def generate_excel_report(tasks_df, summary, difficulty_map):
    buffer = BytesIO()
    
    # Preparar el DataFrame para el reporte
    report_df = tasks_df.copy()
    report_df['estimatedTime'] = report_df['estimatedTimeMinutes'].apply(format_minutes_to_hm)
    report_df['difficulty'] = report_df['difficulty'].map(difficulty_map)
    report_df = report_df[['id', 'name', 'status', 'difficulty', 'estimatedTime']]
    report_df.columns = ['ID', 'Nombre', 'Estado', 'Dificultad', 'Tiempo Estimado']

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        report_df.to_excel(writer, sheet_name='Tareas', index=False)
        
        # Añadir gráfico de progreso
        fig = create_progress_chart(summary)
        if fig:
            img_path = "progress_chart.png"
            fig.savefig(img_path)
            plt.close(fig)
            
            ws = writer.sheets['Tareas']
            img = ExcelImage(img_path)
            # Posicionar la imagen después de la tabla
            img.anchor = f'A{len(report_df) + 3}'
            ws.add_image(img)

    buffer.seek(0)
    return buffer


# --- Interfaz de Streamlit ---

st.set_page_config(page_title="Kankai Pro", layout="wide", page_icon="📝")
manager = TaskManager()

st.title("📝 Kankai Pro")
st.markdown("Organiza tus tareas de forma eficiente y visual.")

# --- Layout Principal ---
main_col, sidebar_col = st.columns([3, 1])

# --- Columna Principal (Tablero y Formulario) ---
with main_col:
    st.header("Tablero Kanban", divider="blue")

    # Columnas del tablero
    col_todo, col_inprogress, col_done = st.columns(3, gap="medium")
    
    board_cols = {
        "todo": col_todo,
        "inprogress": col_inprogress,
        "done": col_done
    }

    tasks = manager.get_tasks()

    for status, col in board_cols.items():
        header_map = {
            "todo": "📌 Por Hacer",
            "inprogress": "⚙️ En Progreso",
            "done": "✅ Finalizado"
        }
        with col:
            st.subheader(header_map[status])
            tasks_in_status = tasks[tasks['status'] == status]
            
            if tasks_in_status.empty:
                st.info("No hay tareas en este estado.")
            
            for _, task in tasks_in_status.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{task['name']}**")
                    st.caption(f"ID: {task['id']}")
                    st.write(f"🕒 {format_minutes_to_hm(task['estimatedTimeMinutes'])} | Dificultad: {manager.difficulty_map.get(task['difficulty'], 'N/A')}")
                    
                    # Botones de acción
                    c1, c2, c3 = st.columns(3)
                    if status == "todo":
                        if c1.button("▶️ Iniciar", key=f"start_{task['id']}", use_container_width=True):
                            manager.update_task_status(task['id'], 'inprogress')
                            st.rerun()
                    if status == "inprogress":
                        if c1.button("⏪ Devolver", key=f"return_{task['id']}", use_container_width=True):
                            manager.update_task_status(task['id'], 'todo')
                            st.rerun()
                        if c2.button("✔️ Finalizar", key=f"finish_{task['id']}", type="primary", use_container_width=True):
                            manager.update_task_status(task['id'], 'done')
                            st.rerun()
                    if status == "done":
                        if c1.button("🗑️ Eliminar", key=f"delete_{task['id']}", use_container_width=True):
                            manager.delete_task(task['id'])
                            st.rerun()
    
    st.header("Añadir Nueva Tarea", divider="gray")
    with st.form("add_task_form", clear_on_submit=True):
        task_name = st.text_input("Nombre de la Tarea", placeholder="Ej: Desarrollar nueva función")
        c1, c2 = st.columns(2)
        task_hours = c1.number_input("Horas Estimadas", min_value=0, step=1)
        task_minutes = c2.number_input("Minutos Estimados", min_value=0, max_value=59, step=1)
        task_difficulty = st.selectbox("Dificultad", options=list(manager.difficulty_map.keys()), format_func=lambda x: manager.difficulty_map[x])
        
        submitted = st.form_submit_button("Añadir Tarea", type="primary", use_container_width=True)
        if submitted:
            total_minutes = (task_hours * 60) + task_minutes
            manager.add_task(task_name, total_minutes, task_difficulty)

# --- Barra Lateral (Progreso y Optimización) ---
with sidebar_col:
    st.header("Análisis", divider="violet")

    # Progreso General
    st.subheader("Progreso General")
    progress_summary = manager.get_progress_summary()
    chart = create_progress_chart(progress_summary)
    if chart:
        st.pyplot(chart)
    st.metric(
        label="Tareas Completadas",
        value=f"{progress_summary['done']} / {progress_summary['total']}",
        delta=f"{progress_summary['percentage']}%"
    )

    # Botón para descargar Excel
    excel_buffer = generate_excel_report(tasks, progress_summary, manager.difficulty_map)
    st.download_button(
        label="📄 Descargar Reporte en Excel",
        data=excel_buffer,
        file_name=f"reporte_kankai_{time.strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    st.divider()

    # Sugerencia de Optimización
    st.subheader("Sugerencia de Optimización")
    if st.button("💡 Sugerir Orden de Tareas", use_container_width=True):
        optimized_tasks = manager.get_optimization_suggestion()
        if optimized_tasks.empty:
            st.info("No hay tareas pendientes para optimizar.")
        else:
            st.markdown("**Orden Sugerido (por dificultad y tiempo):**")
            for i, (_, task) in enumerate(optimized_tasks.iterrows()):
                st.markdown(f"{i+1}. **{task['name']}** ({manager.difficulty_map[task['difficulty']]}, {format_minutes_to_hm(task['estimatedTimeMinutes'])})")

