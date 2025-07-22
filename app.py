import os
import pandas as pd
import pymysql
from sqlalchemy import create_engine # For a more robust database connection
import matplotlib
matplotlib.use('Agg') # A crucial line for running matplotlib on a server
import matplotlib.pyplot as plt
from flask import Flask, render_template

# --- Configuration ---
# IMPORTANT: Update these with your MySQL database credentials.
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'type-your-password', # <-- REPLACE with your MySQL password
    'db': 'your-database'          # <-- REPLACE with the name of your database/schema
}

# Initialize Flask App
app = Flask(__name__)

def create_visualizations():
    """
    Connects to the database, fetches data, and creates two visualizations.
    """
    # Ensure the static directory exists for saving plot images
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    engine = None
    try:
        # --- 1. Connect to MySQL using SQLAlchemy ---
        # This is the recommended way and resolves the UserWarning.
        print("Connecting to the database using SQLAlchemy...")
        connection_string = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['db']}"
        engine = create_engine(connection_string)
        print("Connection successful.")

        # --- 2. Load Data from Tables ---
        print("Fetching data from tables...")
        employees_df = pd.read_sql('SELECT * FROM employees', engine)
        departments_df = pd.read_sql('SELECT * FROM departments', engine)
        projects_df = pd.read_sql('SELECT * FROM project_assignments', engine)
        print(f"Loaded {len(employees_df)} employees, {len(departments_df)} departments, and {len(projects_df)} project assignments.")
        
        # --- 3. [CRITICAL FIX] Clean and Standardize Column Names ---
        # This section renames columns to ensure the merges work correctly.
        
        # In 'departments' table, rename 'id' to 'department_id' for the merge
        if 'id' in departments_df.columns and 'department_id' not in departments_df.columns:
            departments_df.rename(columns={'id': 'department_id'}, inplace=True)
            
        # In 'employees' table, rename 'id' to 'employee_id' for the merge with projects
        if 'id' in employees_df.columns and 'employee_id' not in employees_df.columns:
            employees_df.rename(columns={'id': 'employee_id'}, inplace=True)

        # --- 4. Add Debugging Output ---
        # This helps confirm that the renaming worked as expected.
        print("\n--- Columns after cleaning ---")
        print("Employees Columns:", employees_df.columns.tolist())
        print("Departments Columns:", departments_df.columns.tolist())
        print("Projects Columns:", projects_df.columns.tolist())
        print("----------------------------\n")

        # --- 5. Data Processing and Merging ---
        # This merge links employees to their department names.
        emp_dept_df = pd.merge(employees_df, departments_df, on='department_id', how='left')

        # --- 6. Create Visualization 1: Employees per Department ---
        print("Creating Visualization 1: Employees per Department...")
        plt.style.use('seaborn-v0_8-talk')
        
        if 'department_name' not in emp_dept_df.columns:
            raise KeyError("Column 'department_name' not found. Please check your 'departments' table.")

        dept_counts = emp_dept_df['department_name'].value_counts()

        plt.figure(figsize=(12, 7))
        dept_counts.plot(kind='bar', color='#3498db')
        plt.title('Number of Employees per Department', fontsize=18, fontweight='bold')
        plt.xlabel('Department', fontsize=14)
        plt.ylabel('Number of Employees', fontsize=14)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        plot1_path = os.path.join(static_dir, 'employees_per_department.png')
        plt.savefig(plot1_path)
        plt.close()
        print(f"Saved plot to {plot1_path}")

        # --- 7. Create Visualization 2: Project Distribution by Department ---
        # This merge links projects to employees and their departments.
        print("Creating Visualization 2: Project Distribution by Department...")
        full_df = pd.merge(projects_df, emp_dept_df, on='employee_id', how='left')
        
        # Handle cases where a project might be assigned to an employee with no department
        full_df['department_name'].fillna('Unknown', inplace=True)
        
        project_dept_counts = full_df['department_name'].value_counts()

        plt.figure(figsize=(10, 10))
        plt.pie(project_dept_counts, labels=project_dept_counts.index, autopct='%1.1f%%', startangle=140,
                wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
                colors=plt.cm.viridis_r(range(len(project_dept_counts))))
        plt.title('Project Distribution by Department', fontsize=18, fontweight='bold')
        plt.axis('equal')
        
        plot2_path = os.path.join(static_dir, 'projects_by_department.png')
        plt.savefig(plot2_path)
        plt.close()
        print(f"Saved plot to {plot2_path}")

        return True

    except Exception as e:
        print(f"\n--- AN ERROR OCCURRED ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")
        print("\nThis is likely due to a column name mismatch or a database connection issue.")
        print("Please check the 'Columns after cleaning' output above and your DB_CONFIG settings.")
        print("-------------------------\n")
        return False
    finally:
        # SQLAlchemy engine manages connections automatically, so no need to close.
        print("Script finished processing request.")


@app.route('/')
def index():
    """Renders the main page with the visualizations."""
    success = create_visualizations()
    if success:
        return render_template('index.html',
                               plot1='employees_per_department.png',
                               plot2='projects_by_department.png')
    else:
        return "<h1>Error Generating Visualizations</h1><p>Please check the console output in VS Code for more details on the error.</p>", 500


if __name__ == '__main__':
    # Ensure you have the required libraries in your venv:
    # pip install Flask pandas pymysql matplotlib sqlalchemy
    app.run(debug=True)
