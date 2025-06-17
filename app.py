import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
import math

# --- App Configuration ---
st.set_page_config(layout="wide", page_title="Website Project Simulator")

# --- Main App Interface ---
st.title("🏗️ Website Development Pipeline Simulator")
st.markdown("""
This tool simulates a project pipeline for building multiple websites. 
It accounts for resource constraints and task dependencies to forecast the project timeline.
Use the sidebar to configure your resources, task efforts, and website plans.
""")

# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("⚙️ Global Inputs")

    # --- Resource Configuration ---
    st.subheader("👨‍💻 Team Resources")
    num_designers = st.number_input("Number of Designers", min_value=1, value=1)
    num_content_writers = st.number_input("Number of Content Writers", min_value=1, value=1)
    num_wordpress_devs = st.number_input("Number of WordPress Developers", min_value=1, value=1)
    num_ui_devs = st.number_input("Number of UI (Front-End) Developers", min_value=1, value=2)
    
    resources = {
        'Design': num_designers,
        'Content': num_content_writers,
        'WordPress': num_wordpress_devs,
        'UI': num_ui_devs
    }

    # --- Effort Configuration ---
    st.subheader("⏱️ Task Effort (Man-Days/Page)")
    effort_design = st.number_input("Design Effort per Page", min_value=0.1, value=1.5, step=0.5)
    effort_content = st.number_input("Content Writing Effort per Page", min_value=0.1, value=1.5, step=0.5)
    effort_wordpress = st.number_input("WordPress Dev Effort per Page", min_value=0.1, value=1.0, step=0.5)
    effort_ui = st.number_input("UI Dev Effort per Page", min_value=0.1, value=2.0, step=0.5)
    
    st.subheader("🚀 Go-Live Effort")
    effort_go_live = st.number_input("Go-Live & Setup per Website (Man-Days)", min_value=1.0, value=10.0, step=1.0)

    # --- Website Plan ---
    st.subheader("🌐 Website Plan")
    num_websites = st.number_input("Number of websites to build", min_value=1, value=3)
    
    websites_info = []
    for i in range(num_websites):
        pages = st.number_input(f"Number of pages for Website {i+1}", min_value=1, value=10 + i*5, key=f"pages_{i}")
        websites_info.append({'id': i, 'name': f"Website {i+1}", 'pages': pages})


def run_simulation(resources, websites_info, efforts):
    """
    The core simulation logic, adapted to return structured data instead of printing.
    """
    log_messages = []
    gantt_tasks = [] # To store data for the Gantt chart

    resource_free_on_day = {
        'Design': [0] * resources['Design'],
        'Content': [0] * resources['Content'],
        'WordPress': [0] * resources['WordPress'],
        'UI': [0] * resources['UI']
    }

    tasks = []
    for site in websites_info:
        for page_num in range(1, site['pages'] + 1):
            design_task_id = f"W{site['id']+1}-P{page_num}-Design"
            content_task_id = f"W{site['id']+1}-P{page_num}-Content"
            wordpress_task_id = f"W{site['id']+1}-P{page_num}-WP"
            
            tasks.append({'id': design_task_id, 'website_id': site['id'], 'page': page_num, 'type': 'Design', 'effort': efforts['design'], 'status': 'pending', 'depends_on': None, 'start_day': -1, 'end_day': -1})
            tasks.append({'id': content_task_id, 'website_id': site['id'], 'page': page_num, 'type': 'Content', 'effort': efforts['content'], 'status': 'pending', 'depends_on': design_task_id, 'start_day': -1, 'end_day': -1})
            tasks.append({'id': wordpress_task_id, 'website_id': site['id'], 'page': page_num, 'type': 'WordPress', 'effort': efforts['wordpress'], 'status': 'pending', 'depends_on': content_task_id, 'start_day': -1, 'end_day': -1})
            tasks.append({'id': f"W{site['id']+1}-P{page_num}-UI", 'website_id': site['id'], 'page': page_num, 'type': 'UI', 'effort': efforts['ui'], 'status': 'pending', 'depends_on': wordpress_task_id, 'start_day': -1, 'end_day': -1})

    for site in websites_info:
        ui_tasks_for_site = [t['id'] for t in tasks if t['website_id'] == site['id'] and t['type'] == 'UI']
        go_live_resources_count = resources['WordPress'] + resources['UI']
        go_live_effort = efforts['go_live'] / go_live_resources_count if go_live_resources_count > 0 else float('inf')
        tasks.append({'id': f"W{site['id']+1}-GoLive", 'website_id': site['id'], 'page': 'N/A', 'type': 'Go-Live', 'effort': go_live_effort, 'status': 'pending', 'depends_on': ui_tasks_for_site, 'start_day': -1, 'end_day': -1})

    completed_tasks = {}
    active_websites = set()
    website_start_times = {}
    website_end_times = {}
    website_actual_start_logged = set()
    current_day = 0
    time_step = 0.5 

    while len(completed_tasks) < len(tasks):
        if current_day > 1000: # Safety break to prevent infinite loops
            log_messages.append("Error: Simulation timed out. Check constraints.")
            break

        websites_in_progress = {t['website_id'] for t in tasks if t['status'] in ['inprogress', 'complete']}
        
        if len(active_websites) < 2:
            # Sort websites by their ID to ensure consistent activation order
            sorted_sites = sorted(websites_info, key=lambda x: x['id'])
            for site in sorted_sites:
                if site['id'] not in active_websites and site['id'] not in website_end_times:
                    active_websites.add(site['id'])
                    log_messages.append(f"[{current_day:>5.1f} days] ✅ WEBSITE {site['id']+1} activated (eligible for work).")
                    break
        
        # Prioritize tasks from websites that were activated first
        tasks.sort(key=lambda x: (x['website_id'], x['page'] if isinstance(x['page'], int) else float('inf')))

        for task in tasks:
            if task['status'] != 'pending' or task['website_id'] not in active_websites:
                continue

            deps_met = False
            if task['depends_on'] is None:
                deps_met = True
            elif isinstance(task['depends_on'], str) and task['depends_on'] in completed_tasks:
                 deps_met = True
            elif isinstance(task['depends_on'], list) and all(dep in completed_tasks for dep in task['depends_on']):
                deps_met = True
            
            if not deps_met:
                continue
            
            task_type_for_resource = 'WordPress' if task['type'] == 'Go-Live' else task['type']
            dep_end_day = 0
            if isinstance(task['depends_on'], str) and task['depends_on'] in completed_tasks:
                dep_end_day = completed_tasks[task['depends_on']]
            elif isinstance(task['depends_on'], list) and deps_met:
                dep_end_day = max(completed_tasks.get(dep, 0) for dep in task['depends_on']) if task['depends_on'] else 0

            earliest_start_time = float('inf')
            resource_to_assign = -1
            resource_pool = resource_free_on_day.get(task_type_for_resource)
            
            if task['type'] == 'Go-Live':
                 resource_pool = resource_free_on_day['WordPress'] + resource_free_on_day['UI']

            for i, free_day in enumerate(resource_pool):
                possible_start_time = max(free_day, dep_end_day)
                if possible_start_time < earliest_start_time:
                    earliest_start_time = possible_start_time
                    resource_to_assign = i
            
            if resource_to_assign != -1 and earliest_start_time <= current_day:
                task['status'] = 'inprogress'
                task['start_day'] = earliest_start_time
                task['end_day'] = earliest_start_time + task['effort']
                
                # Add to Gantt data
                #gantt_tasks.append(dict(
                #    Task=task['id'], 
                #    Start=f"{pd.to_datetime('2024-01-01') + pd.to_timedelta(task['start_day'], 'D')}", 
                #    Finish=f"{pd.to_datetime('2024-01-01') + pd.to_timedelta(task['end_day'], 'D')}", 
                #    Resource=task['type']
                #))
                project_start_date = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
                gantt_tasks.append(dict(
                    Task=f"Website {task['website_id']+1} - {task['type']}",
                    Start = f"{project_start_date + pd.to_timedelta(task['start_day'], 'D')}",
                    Finish = f"{project_start_date + pd.to_timedelta(task['end_day'], 'D')}",
                    #Start=f"{pd.to_datetime('2024-01-01') + pd.to_timedelta(task['start_day'], 'D')}", 
                    #Finish=f"{pd.to_datetime('2024-01-01') + pd.to_timedelta(task['end_day'], 'D')}", 
                    Resource=task['type']
                ))


                if task['website_id'] not in website_actual_start_logged:
                    website_actual_start_logged.add(task['website_id'])
                    website_start_times[task['website_id']] = task['start_day']
                    log_messages.append(f"[{task['start_day']:>5.1f} days] 🚀 WORK has started on Website {task['website_id']+1} (Task: {task['type']}).")

                if task['type'] == 'Go-Live':
                    if resource_to_assign < len(resource_free_on_day['WordPress']):
                        resource_free_on_day['WordPress'][resource_to_assign] = task['end_day']
                    else:
                        idx = resource_to_assign - len(resource_free_on_day['WordPress'])
                        resource_free_on_day['UI'][idx] = task['end_day']
                else:
                    resource_pool[resource_to_assign] = task['end_day']

        current_day += time_step
        
        for task in tasks:
            if task['status'] == 'inprogress' and current_day >= task['end_day']:
                task['status'] = 'complete'
                completed_tasks[task['id']] = task['end_day']
                if task['type'] == 'Go-Live':
                    site_id = task['website_id']
                    website_end_times[site_id] = task['end_day']
                    active_websites.remove(site_id)
                    log_messages.append(f"[{task['end_day']:>5.1f} days] 🎉 WEBSITE {site_id+1} IS COMPLETE!")

    return website_start_times, website_end_times, log_messages, gantt_tasks

# --- Main App Logic ---
if st.sidebar.button("▶️ Run Simulation"):
    
    efforts_dict = {
        'design': effort_design,
        'content': effort_content,
        'wordpress': effort_wordpress,
        'ui': effort_ui,
        'go_live': effort_go_live
    }
    
    starts, ends, logs, gantt_data = run_simulation(resources, websites_info, efforts_dict)

    st.header("📊 Results")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Project Summary")
        if ends:
            total_duration = max(ends.values())
            st.metric("Total Project Duration", f"{math.ceil(total_duration)} Business Days")

            summary_data = []
            for site_id, end_time in sorted(ends.items()):
                start_time = starts.get(site_id, 0)
                summary_data.append({
                    "Website": f"Website {site_id+1}",
                    "Start Day": f"{start_time:.1f}",
                    "End Day": f"{end_time:.1f}",
                    "Duration (Days)": math.ceil(end_time - start_time)
                })
            st.dataframe(pd.DataFrame(summary_data))
        else:
            st.warning("Simulation did not complete.")

    with col2:
        st.subheader("📝 Simulation Log")
        st.text_area("Log Output", value="\n".join(logs), height=300)

    # --- Gantt Chart ---
    if gantt_data:
        st.header("🗓️ Project Gantt Chart")
        st.markdown("This chart visualizes the timeline for every single task in the project.")
        
        # Assign colors to resources
        colors = {
            'Design': 'rgb(255, 127, 14)', 
            'Content': 'rgb(44, 160, 44)', 
            'WordPress': 'rgb(31, 119, 180)',
            'UI': 'rgb(214, 39, 40)',
            'Go-Live': 'rgb(148, 103, 189)'
        }
        
        df = pd.DataFrame(gantt_data)
        fig = ff.create_gantt(df, colors=colors, index_col='Resource', show_colorbar=True, group_tasks=True, showgrid_x=True, title="Task-Level Timeline")
        from datetime import timedelta

        start = df['Start'].min()
        end = df['Finish'].max()

        curr_date = pd.to_datetime(start)
        while curr_date <= pd.to_datetime(end):
            if curr_date.weekday() >= 5:  # Saturday=5, Sunday=6
                fig.add_vrect(
                    x0=curr_date,
                    x1=curr_date + timedelta(days=1),
                    fillcolor="lightgray",
                    opacity=0.3,
                    layer="below",
                    line_width=0,
                )
            curr_date += timedelta(days=1)

        
        # Reverse the order of tasks on the y-axis to be more chronological
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=1200)  # Adjust height as needed
        fig.update_layout(
            xaxis=dict(
                tickformat="%b %d (%a)",
                tickangle=-45
            )
        )

        
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Configure your project in the sidebar and click 'Run Simulation' to see the results.")
