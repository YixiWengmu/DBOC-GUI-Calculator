import re
from constants import PRIMITIVE_QUANTUM_NUMBERS


def read_file(file_path):
    """
    Read the content of a file.

    Parameters
    ----------
    file_path : str
        Path to the file.

    Returns
    -------
    str
        File content.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


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


def split_alpha_beta_coefficients(coefficients, electron_spins):
    """Split molecular orbital coefficients into alpha and beta blocks."""
    coefficients_alpha = []
    coefficients_beta = []
    coeff_len = len(coefficients)
    coeff_index = 0

    for spin in electron_spins:
        if spin == "Alpha":
            coefficients_alpha.append(coefficients[coeff_index])
        else:
            coefficients_beta.append(coefficients[coeff_index])
        coeff_index = (coeff_index + 1) % coeff_len

    return coefficients_alpha, coefficients_beta


def extract_quantum_numbers(primitives):
    """Convert primitive orbital labels into (l, m, n) quantum numbers."""
    l_values, m_values, n_values = [], [], []

    for item in primitives:
        l_val, m_val, n_val = PRIMITIVE_QUANTUM_NUMBERS[item[1]]
        l_values.append(l_val)
        m_values.append(m_val)
        n_values.append(n_val)

    return l_values, m_values, n_values


def build_primitives(parsed_entry):
    """Build primitive tuples with quantum numbers included."""
    primitive_info = parsed_entry["primitive_info"]
    exponents = parsed_entry["exponents"]
    coordinates = parsed_entry["center_coordinates"]
    centers = parsed_entry["centers"]

    l_values, m_values, n_values = extract_quantum_numbers(primitive_info)
    return list(zip(centers, l_values, m_values, n_values, exponents, coordinates))


def build_gaussian_basis(primitives, prefix):
    """Build Gaussian basis dictionaries."""
    molecule = []

    for _, l_val, m_val, n_val, exponent, coordinates in primitives:
        coordinates = [float(x) for x in coordinates]
        molecule.append({
            f"l{prefix}": l_val,
            f"m{prefix}": m_val,
            f"n{prefix}": n_val,
            f"exp{prefix}": exponent,
            f"coordinates{prefix}": coordinates
        })

    return molecule


def parse_single_wfx_content(content):
    """
    Parse a single WFX content block into structured data.
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


def parse_files(file_map):
    """
    Read and parse all six WFX files.

    Parameters
    ----------
    file_map : dict
        Mapping like {'x1': path, 'x2': path, ...}

    Returns
    -------
    dict
        Parsed data for all six files.
    """
    contents = {key: read_file(path) for key, path in file_map.items()}
    return {key: parse_single_wfx_content(content) for key, content in contents.items()}