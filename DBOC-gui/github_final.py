import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import tkinter.font as tkfont
import numpy as np
import re
import threading
import time


# ==========================
# Main window configuration
# ==========================
root = tk.Tk()
root.title("DBOC Calculation")
root.geometry("900x650")

default_font = tkfont.nametofont("TkDefaultFont")
default_font.configure(size=9)
root.option_add("*Font", default_font)


# ==========================
# Global variables
# ==========================
f_path_x1 = ""
f_path_x2 = ""
f_path_y1 = ""
f_path_y2 = ""
f_path_z1 = ""
f_path_z2 = ""

file_paths = []
calculation_in_progress = False


# ==========================
# Progress bar and status bar
# ==========================
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
progress_bar.pack(pady=5, fill=tk.X, padx=20)
progress_bar.pack_forget()

status_label = tk.Label(root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
status_label.pack(side=tk.BOTTOM, fill=tk.X)


# ==========================
# UI helper functions
# ==========================
def update_progress(step, total_steps=100):
    """Update the progress bar."""
    progress = (step / total_steps) * 100
    progress_var.set(progress)
    root.update_idletasks()


def update_status(message):
    """Update the status bar text."""
    status_label.config(text=message)
    root.update_idletasks()


def show_result(text):
    """Display text in the result area."""
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, text)
    root.update_idletasks()


# ==========================
# File handling functions
# ==========================
def read_file(file_path):
    """
    Read the content of a file.

    Parameters
    ----------
    file_path : str
        Path to the file.

    Returns
    -------
    str or None
        File content if successful, otherwise None.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        show_result(f"File read error: {str(e)}")
        return None


def assign_files():
    """
    Assign the selected files to the six directional slots
    based on filename patterns.
    """
    global f_path_x1, f_path_x2, f_path_y1, f_path_y2, f_path_z1, f_path_z2

    f_path_x1 = f_path_x2 = f_path_y1 = f_path_y2 = f_path_z1 = f_path_z2 = ""

    for path in file_paths:
        filename = path.split("\\")[-1] if "\\" in path else path.split("/")[-1]

        if re.search(r"\+x\d+\.\d+", filename):
            f_path_x1 = path
        elif re.search(r"\-x\d+\.\d+", filename):
            f_path_x2 = path
        elif re.search(r"\+y\d+\.\d+", filename):
            f_path_y1 = path
        elif re.search(r"\-y\d+\.\d+", filename):
            f_path_y2 = path
        elif re.search(r"\+z\d+\.\d+", filename):
            f_path_z1 = path
        elif re.search(r"\-z\d+\.\d+", filename):
            f_path_z2 = path

    if all([f_path_x1, f_path_x2, f_path_y1, f_path_y2, f_path_z1, f_path_z2]):
        show_result("File assignment successful.\nClick 'Start Calculation' to proceed.")
    else:
        show_result(
            "File naming pattern not recognized.\n"
            "Please ensure filenames contain +x/-x/+y/-y/+z/-z labels."
        )


def select_files():
    """Open a dialog and select exactly six WFX files."""
    global file_paths, calculation_in_progress

    if calculation_in_progress:
        show_result("Please wait until the current calculation is finished.")
        return

    files = filedialog.askopenfilenames(
        title="Select 6 WFX files",
        filetypes=[("WFX files", "*.wfx"), ("All files", "*.*")]
    )

    if len(files) != 6:
        show_result("Please select exactly 6 files.")
        return

    file_paths = list(files)
    assign_files()

    print("Selected 6 files:")
    for i, path in enumerate(file_paths, 1):
        print(f"{i}. {path}")

    show_result("Selected 6 files:\n" + "\n".join(file_paths))


def validate_assigned_files():
    """Return True if all six directional files have been assigned."""
    return all([f_path_x1, f_path_x2, f_path_y1, f_path_y2, f_path_z1, f_path_z2])


def load_all_file_contents():
    """
    Read all six WFX files.

    Returns
    -------
    dict or None
        Dictionary of file contents if successful, otherwise None.
    """
    update_status("Reading X-direction files...")
    content_x1 = read_file(f_path_x1)
    content_x2 = read_file(f_path_x2)
    update_progress(10)

    update_status("Reading Y-direction files...")
    content_y1 = read_file(f_path_y1)
    content_y2 = read_file(f_path_y2)
    update_progress(15)

    update_status("Reading Z-direction files...")
    content_z1 = read_file(f_path_z1)
    content_z2 = read_file(f_path_z2)
    update_progress(20)

    contents = {
        "x1": content_x1, "x2": content_x2,
        "y1": content_y1, "y2": content_y2,
        "z1": content_z1, "z2": content_z2
    }

    if not all(contents.values()):
        return None

    return contents


# ==========================
# WFX parsing functions
# ==========================
def extract_nuclear_coordinates(content):
    """Extract nuclear Cartesian coordinates from a WFX file."""
    coordinates = re.findall(
        r"([-+]?\d+\.\d+e[+-]\d+)",
        re.search(
            r"<Nuclear Cartesian Coordinates>(.*?)</Nuclear Cartesian Coordinates>",
            content,
            re.DOTALL
        ).group(1)
    )
    return [coordinates[i:i + 3] for i in range(0, len(coordinates), 3)]


def extract_nuclear_names_and_centers(content, coordinates):
    """Extract nuclear names and primitive-center coordinates."""
    nuclear_names = re.findall(
        r"<Nuclear Names>\s*(.*?)\s*</Nuclear Names>",
        content,
        re.DOTALL
    )[0].split()

    primitive_centers = re.findall(
        r"<Primitive Centers>\s*(.*?)\s*</Primitive Centers>",
        content,
        re.DOTALL
    )[0].split()

    centers = []
    coords = []

    for primitive_center in primitive_centers:
        index = int(primitive_center) - 1
        centers.append(nuclear_names[index])
        coords.append(coordinates[index])

    return centers, coords


def extract_primitive_types(content):
    """Extract primitive orbital labels from a WFX file."""
    primitive_types = re.findall(
        r"<Primitive Types>\s*(.*?)\s*</Primitive Types>",
        content,
        re.DOTALL
    )[0].split()

    orbital_map = {
        "1": "S", "2": "PX", "3": "PY", "4": "PZ",
        "5": "DXX", "6": "DYY", "7": "DZZ", "8": "DXY", "9": "DXZ", "10": "DYZ",
        "11": "FXXX", "12": "FYYY", "13": "FZZZ", "14": "FXXY", "15": "FXXZ",
        "16": "FYYZ", "17": "FXYY", "18": "FXZZ", "19": "FYZZ", "20": "FXYZ",
        "21": "GXXXX", "22": "GYYYY", "23": "GZZZZ", "24": "GXXXY", "25": "GXXXZ",
        "26": "GXYYY", "27": "GYYYZ", "28": "GXZZZ", "29": "GYZZZ", "30": "GXXYY",
        "31": "GXXZZ", "32": "GYYZZ", "33": "GXXYZ", "34": "GXYYZ", "35": "GXYZZ"
    }

    return [orbital_map[i] for i in primitive_types if i in orbital_map]


def extract_primitive_exponents(content):
    """Extract primitive Gaussian exponents."""
    primitive_exponents = re.findall(
        r"(\d+\.\d+e[+-]\d+)",
        re.search(r"<Primitive Exponents>(.*?)</Primitive Exponents>", content, re.DOTALL).group(1)
    )
    return [float(x) for x in primitive_exponents]


def extract_electron_spin_types(content):
    """Extract molecular orbital spin types."""
    spin_types = re.findall(
        r"<Molecular Orbital Spin Types>\s*(.*?)\s*</Molecular Orbital Spin Types>",
        content,
        re.DOTALL
    )[0].split()

    if "and" in spin_types:
        alpha_list = []
        beta_list = []
        for item in spin_types:
            if item == "Alpha":
                alpha_list.append(item)
            elif item == "Beta":
                beta_list.append(item)
        return alpha_list + beta_list

    return spin_types


def extract_mo_coefficients(content):
    """Extract molecular orbital coefficients."""
    primitive_coefficients = re.findall(
        r"<MO Number>\s+(\d+)\s+</MO Number>\s+([\d\.\-\se+]+)",
        content
    )

    mo_coefficients = [
        (mo_num, re.findall(r"([-+]?\d+\.\d+e[+-]\d+)", coeffs))
        for mo_num, coeffs in primitive_coefficients
    ]

    return [[float(coeff) for coeff in coeffs] for _, coeffs in mo_coefficients]


def split_alpha_beta_coefficients(coefficients, electron):
    """Split molecular orbital coefficients into alpha and beta blocks."""
    coefficients_alpha = []
    coefficients_beta = []
    coeff_len = len(coefficients)
    coeff_index = 0

    for e in electron:
        if e == "Alpha":
            coefficients_alpha.append(coefficients[coeff_index])
        else:
            coefficients_beta.append(coefficients[coeff_index])
        coeff_index = (coeff_index + 1) % coeff_len

    return coefficients_alpha, coefficients_beta


def parse_single_wfx_content(content):
    """
    Parse a single WFX content block into structured data.

    Returns
    -------
    dict
        Parsed information for one WFX file.
    """
    coordinates = extract_nuclear_coordinates(content)
    centers, center_coordinates = extract_nuclear_names_and_centers(content, coordinates)
    types = extract_primitive_types(content)
    exponents = extract_primitive_exponents(content)
    electron_spins = extract_electron_spin_types(content)
    mo_coefficients = extract_mo_coefficients(content)
    alpha_coefficients, beta_coefficients = split_alpha_beta_coefficients(mo_coefficients, electron_spins)

    primitive_info = list(zip(centers, types, exponents, center_coordinates))

    return {
        "coordinates": coordinates,
        "centers": centers,
        "center_coordinates": center_coordinates,
        "types": types,
        "exponents": exponents,
        "electron_spins": electron_spins,
        "mo_coefficients": mo_coefficients,
        "alpha_coefficients": alpha_coefficients,
        "beta_coefficients": beta_coefficients,
        "primitive_info": primitive_info
    }


def parse_all_wfx_contents(contents):
    """Parse all six WFX files."""
    update_status("Extracting coordinates and basis information...")

    parsed_data = {
        key: parse_single_wfx_content(content)
        for key, content in contents.items()
    }

    update_progress(50)
    return parsed_data


# ==========================
# Basis-function construction
# ==========================
PRIMITIVE_QUANTUM_NUMBERS = {
    "S": (0, 0, 0), "PX": (1, 0, 0), "PY": (0, 1, 0), "PZ": (0, 0, 1),
    "DXX": (2, 0, 0), "DYY": (0, 2, 0), "DZZ": (0, 0, 2),
    "DXY": (1, 1, 0), "DXZ": (1, 0, 1), "DYZ": (0, 1, 1),
    "FXXX": (3, 0, 0), "FYYY": (0, 3, 0), "FZZZ": (0, 0, 3),
    "FXXY": (2, 1, 0), "FXXZ": (2, 0, 1), "FYYZ": (0, 2, 1),
    "FXYY": (1, 2, 0), "FXZZ": (1, 0, 2), "FYZZ": (0, 1, 2), "FXYZ": (1, 1, 1),
    "GXXXX": (4, 0, 0), "GYYYY": (0, 4, 0), "GZZZZ": (0, 0, 4), "GXXXY": (3, 1, 0),
    "GXXXZ": (3, 0, 1), "GXYYY": (1, 3, 0), "GYYYZ": (0, 3, 1),
    "GXZZZ": (1, 0, 3), "GYZZZ": (0, 1, 3), "GXXYY": (2, 2, 0), "GXXZZ": (2, 0, 2),
    "GYYZZ": (0, 2, 2), "GXXYZ": (2, 1, 1), "GXYYZ": (1, 2, 1), "GXYZZ": (1, 1, 2)
}


def extract_quantum_numbers(primitives, primitive_mapping):
    """Convert primitive orbital labels into (l, m, n) quantum numbers."""
    l_values, m_values, n_values = [], [], []

    for item in primitives:
        l, m, n = primitive_mapping[item[1]]
        l_values.append(l)
        m_values.append(m)
        n_values.append(n)

    return l_values, m_values, n_values


def build_primitives(parsed_entry):
    """Build primitive tuples with quantum numbers included."""
    primitive_info = parsed_entry["primitive_info"]
    exponents = parsed_entry["exponents"]
    coordinates = parsed_entry["center_coordinates"]
    centers = parsed_entry["centers"]

    l_values, m_values, n_values = extract_quantum_numbers(primitive_info, PRIMITIVE_QUANTUM_NUMBERS)

    return list(zip(centers, l_values, m_values, n_values, exponents, coordinates))


def build_gaussian_basis(primitives, prefix):
    """
    Build Gaussian basis dictionaries.

    Parameters
    ----------
    primitives : list
        Primitive basis information.
    prefix : str
        Prefix used in dictionary keys, typically '1' or '2'.

    Returns
    -------
    list
        List of Gaussian basis dictionaries.
    """
    molecule = []

    for _, l_val, m_val, n_val, exponent, coordinates in primitives:
        coordinates = [float(x) for x in coordinates]
        molecule.append({
            f"l{prefix}": l_val,
            f"m{prefix}": m_val,
            f"n{prefix}": n_val,
            f"exp{prefix}": exponent,
            f"coordinates{prefix}": np.array(coordinates)
        })

    return molecule


def build_all_molecules(parsed_data):
    """Build Gaussian basis sets for all six directional files."""
    update_status("Building Gaussian basis functions...")

    primitives_x1 = build_primitives(parsed_data["x1"])
    primitives_x2 = build_primitives(parsed_data["x2"])
    primitives_y1 = build_primitives(parsed_data["y1"])
    primitives_y2 = build_primitives(parsed_data["y2"])
    primitives_z1 = build_primitives(parsed_data["z1"])
    primitives_z2 = build_primitives(parsed_data["z2"])

    molecules = {
        "x1": build_gaussian_basis(primitives_x1, "1"),
        "x2": build_gaussian_basis(primitives_x2, "2"),
        "y1": build_gaussian_basis(primitives_y1, "1"),
        "y2": build_gaussian_basis(primitives_y2, "2"),
        "z1": build_gaussian_basis(primitives_z1, "1"),
        "z2": build_gaussian_basis(primitives_z2, "2"),
    }

    update_progress(65)
    return molecules


# ==========================
# Overlap integral functions
# ==========================
def compute_directional_overlap_component(molecule1, molecule2, axis_name):
    """
    Compute overlap components for one Cartesian direction.

    Parameters
    ----------
    molecule1, molecule2 : list
        Gaussian basis dictionaries.
    axis_name : str
        One of 'l', 'm', or 'n'.

    Returns
    -------
    numpy.ndarray
        Overlap component matrix.
    """
    index_map = {"l": 0, "m": 1, "n": 2}

    def calculate_component(power1, power2, a, b, coord_a, coord_b):
        p = a + b
        q = a * b / p
        r = np.array([coord_a - coord_b])
        r2 = np.dot(r, r)

        s = np.zeros((power1 + 1, power2 + 1))
        s[0, 0] = np.exp(-q * r2) * (np.pi / p) ** 0.5

        for i in range(1, power1 + 1):
            s[i, 0] = -b / p * (coord_a - coord_b) * s[i - 1, 0]
            if i > 1:
                s[i, 0] += 1 / (2 * p) * (i - 1) * s[i - 2, 0]

        for j in range(1, power2 + 1):
            s[0, j] = a / p * (coord_a - coord_b) * s[0, j - 1]
            if j > 1:
                s[0, j] += 1 / (2 * p) * (j - 1) * s[0, j - 2]

        for i in range(1, power1 + 1):
            for j in range(1, power2 + 1):
                s[i, j] = -b / p * (coord_a - coord_b) * s[i - 1, j] + 1 / (2 * p) * (
                    (i - 1) * s[i - 2, j] + j * s[i - 1, j - 1]
                )

        return s[power1, power2]

    overlap_matrix = np.zeros((len(molecule1), len(molecule2)))
    coord_index = index_map[axis_name]

    for i in range(len(molecule1)):
        for j in range(len(molecule2)):
            overlap_matrix[i, j] = calculate_component(
                molecule1[i][f"{axis_name}1"],
                molecule2[j][f"{axis_name}2"],
                molecule1[i]["exp1"],
                molecule2[j]["exp2"],
                molecule1[i]["coordinates1"][coord_index],
                molecule2[j]["coordinates2"][coord_index]
            )

    return overlap_matrix


def compute_atomic_overlap_matrix(molecule1, molecule2):
    """Compute the atomic orbital overlap matrix."""
    s_l = compute_directional_overlap_component(molecule1, molecule2, "l")
    s_m = compute_directional_overlap_component(molecule1, molecule2, "m")
    s_n = compute_directional_overlap_component(molecule1, molecule2, "n")
    return np.array(s_n * s_m * s_l)


def compute_mo_overlap_determinant(overlap_matrix, coeff_alpha_1, coeff_alpha_2, coeff_beta_1, coeff_beta_2):
    """
    Compute the determinant-based molecular orbital overlap measure.
    """
    m_alpha = len(coeff_alpha_1)
    n_basis = len(coeff_alpha_1[0])
    m_beta = len(coeff_beta_1)

    alpha_matrix = np.zeros((m_alpha, m_alpha))
    for vi_alpha in range(m_alpha):
        for ui_alpha in range(m_alpha):
            value = 0
            for v_alpha in range(n_basis):
                for u_alpha in range(n_basis):
                    value += (
                        coeff_alpha_1[vi_alpha][v_alpha]
                        * coeff_alpha_2[ui_alpha][u_alpha]
                        * overlap_matrix[v_alpha][u_alpha]
                    )
            alpha_matrix[vi_alpha][ui_alpha] = value

    beta_matrix = np.zeros((m_beta, m_beta))
    for vi_beta in range(m_beta):
        for ui_beta in range(m_beta):
            value = 0
            for v_beta in range(n_basis):
                for u_beta in range(n_basis):
                    value += (
                        coeff_beta_1[vi_beta][v_beta]
                        * coeff_beta_2[ui_beta][u_beta]
                        * overlap_matrix[v_beta][u_beta]
                    )
            beta_matrix[vi_beta][ui_beta] = value

    alpha_det = np.linalg.det(alpha_matrix)
    beta_det = np.linalg.det(beta_matrix)

    return abs(alpha_det) * abs(beta_det), alpha_det, beta_det


def compute_all_directional_overlaps(parsed_data, molecules):
    """Compute overlap quantities for x, y, and z directions."""
    update_status("Computing overlap integrals...")

    x_atomic_overlap = compute_atomic_overlap_matrix(molecules["x1"], molecules["x2"])
    update_progress(75)

    y_atomic_overlap = compute_atomic_overlap_matrix(molecules["y1"], molecules["y2"])
    update_progress(80)

    z_atomic_overlap = compute_atomic_overlap_matrix(molecules["z1"], molecules["z2"])
    update_progress(85)

    update_status("Computing molecular orbital overlaps...")

    x_s_pm, x_alpha_det, x_beta_det = compute_mo_overlap_determinant(
        x_atomic_overlap,
        parsed_data["x1"]["alpha_coefficients"], parsed_data["x2"]["alpha_coefficients"],
        parsed_data["x1"]["beta_coefficients"], parsed_data["x2"]["beta_coefficients"]
    )
    update_progress(90)

    y_s_pm, y_alpha_det, y_beta_det = compute_mo_overlap_determinant(
        y_atomic_overlap,
        parsed_data["y1"]["alpha_coefficients"], parsed_data["y2"]["alpha_coefficients"],
        parsed_data["y1"]["beta_coefficients"], parsed_data["y2"]["beta_coefficients"]
    )
    update_progress(95)

    z_s_pm, z_alpha_det, z_beta_det = compute_mo_overlap_determinant(
        z_atomic_overlap,
        parsed_data["z1"]["alpha_coefficients"], parsed_data["z2"]["alpha_coefficients"],
        parsed_data["z1"]["beta_coefficients"], parsed_data["z2"]["beta_coefficients"]
    )
    update_progress(98)

    return {
        "x_s_pm": x_s_pm,
        "y_s_pm": y_s_pm,
        "z_s_pm": z_s_pm,
        "x_alpha_det": x_alpha_det,
        "x_beta_det": x_beta_det,
        "y_alpha_det": y_alpha_det,
        "y_beta_det": y_beta_det,
        "z_alpha_det": z_alpha_det,
        "z_beta_det": z_beta_det,
    }


# ==========================
# Final result calculation
# ==========================
def calculate_denominator(ma_value, mn_value, step_value):
    """Compute the denominator in the final DBOC-related expression."""
    return (
        2
        * (ma_value * 1822.88847977884 - mn_value)
        * step_value ** 2
        * 1.88972612462577 ** 2
        / 219474.63
    )


def read_user_parameters():
    """
    Read user-entered physical parameters from the GUI.

    Returns
    -------
    tuple
        (ma, mn, step)
    """
    ma = float(ma_entry.get())
    mn = float(mn_entry.get())
    step = float(step_entry.get())
    return ma, mn, step


def compute_final_result(overlap_results):
    """
    Compute the final scalar result from directional overlaps and user parameters.
    """
    sum_value = 3 - overlap_results["x_s_pm"] - overlap_results["y_s_pm"] - overlap_results["z_s_pm"]
    ma, mn, step = read_user_parameters()
    denominator = calculate_denominator(ma, mn, step)
    result = sum_value / denominator / 2
    return result, sum_value


def format_final_output(overlap_results, result, sum_value, run_time):
    """Format the final result string shown in the GUI."""
    selected_files_text = "Selected 6 files:\n" + "\n".join(file_paths)

    return (
        "Calculation completed.\n\n"
        f"{selected_files_text}\n\n"
        f"X-direction overlap integral: {overlap_results['x_s_pm']}\n"
        f"Y-direction overlap integral: {overlap_results['y_s_pm']}\n"
        f"Z-direction overlap integral: {overlap_results['z_s_pm']}\n"
        f"Sum value: {sum_value}\n\n"
        f"Final result: {result}\n\n"
        f"Program runtime: {run_time:.2f} s\n"
    )


# ==========================
# Main calculation workflow
# ==========================
def run_calculation_pipeline():
    """
    Execute the full DBOC calculation workflow in a modular pipeline.
    """
    start_time = time.time()
    update_status("Initializing calculation...")

    selected_files_text = "Selected 6 files:\n" + "\n".join(file_paths)
    show_result(f"{selected_files_text}\n\nCalculation in progress...\n")
    update_progress(5)

    if not validate_assigned_files():
        show_result("Please select and assign all six files correctly before calculation.")
        return

    contents = load_all_file_contents()
    if contents is None:
        show_result("File reading failed. Please check file paths and permissions.")
        return

    parsed_data = parse_all_wfx_contents(contents)
    molecules = build_all_molecules(parsed_data)
    overlap_results = compute_all_directional_overlaps(parsed_data, molecules)

    update_status("Computing final result...")

    try:
        result, sum_value = compute_final_result(overlap_results)
    except ValueError:
        show_result("Please enter valid values for Ma (atomic mass), Mn (nuclear mass), and step.")
        return

    run_time = time.time() - start_time
    final_output = format_final_output(overlap_results, result, sum_value, run_time)

    show_result(final_output)
    update_progress(100)
    update_status("Calculation completed")


# ==========================
# Threading functions
# ==========================
def calculation_thread():
    """Run the calculation in a separate thread to keep the GUI responsive."""
    global calculation_in_progress

    try:
        calculation_in_progress = True
        select_btn.config(state=tk.DISABLED)
        calc_btn.config(state=tk.DISABLED)
        progress_bar.pack(pady=5, fill=tk.X, padx=20)

        run_calculation_pipeline()

    except Exception as e:
        show_result(f"An error occurred during calculation: {str(e)}")
    finally:
        calculation_in_progress = False
        select_btn.config(state=tk.NORMAL)
        calc_btn.config(state=tk.NORMAL)
        progress_bar.pack_forget()
        progress_var.set(0)


def start_calculation():
    """Validate input state and start the calculation thread."""
    if calculation_in_progress:
        show_result("A calculation is already in progress. Please wait.")
        return

    if not validate_assigned_files():
        show_result("Please select and assign all six files correctly first.")
        return

    thread = threading.Thread(target=calculation_thread)
    thread.daemon = True
    thread.start()


# ==========================
# GUI layout
# ==========================
select_btn = tk.Button(root, text="Select 6 WFX Files", command=select_files)
select_btn.pack(pady=10)

param_frame = tk.Frame(root)
param_frame.pack(pady=10)

tk.Label(param_frame, text="Ma:").grid(row=0, column=0, padx=5)
ma_entry = tk.Entry(param_frame, width=12)
ma_entry.grid(row=0, column=1, padx=5)

tk.Label(param_frame, text="Mn:").grid(row=0, column=2, padx=5)
mn_entry = tk.Entry(param_frame, width=12)
mn_entry.grid(row=0, column=3, padx=5)

tk.Label(param_frame, text="Step:").grid(row=0, column=4, padx=5)
step_entry = tk.Entry(param_frame, width=12)
step_entry.grid(row=0, column=5, padx=5)
step_entry.insert(0, "0.001")

calc_btn = tk.Button(root, text="Start Calculation", command=start_calculation)
calc_btn.pack(pady=10)

result_text = scrolledtext.ScrolledText(root, width=100, height=24)
result_text.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

root.mainloop()