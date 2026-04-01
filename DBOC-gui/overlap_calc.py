import numpy as np
from wfx_parser import build_primitives, build_gaussian_basis


def compute_directional_overlap_component(molecule1, molecule2, axis_name):
    """
    Compute overlap components for one Cartesian direction.
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


def build_all_molecules(parsed_data):
    """Build Gaussian basis sets for all six directional files."""
    primitives_x1 = build_primitives(parsed_data["x1"])
    primitives_x2 = build_primitives(parsed_data["x2"])
    primitives_y1 = build_primitives(parsed_data["y1"])
    primitives_y2 = build_primitives(parsed_data["y2"])
    primitives_z1 = build_primitives(parsed_data["z1"])
    primitives_z2 = build_primitives(parsed_data["z2"])

    return {
        "x1": build_gaussian_basis(primitives_x1, "1"),
        "x2": build_gaussian_basis(primitives_x2, "2"),
        "y1": build_gaussian_basis(primitives_y1, "1"),
        "y2": build_gaussian_basis(primitives_y2, "2"),
        "z1": build_gaussian_basis(primitives_z1, "1"),
        "z2": build_gaussian_basis(primitives_z2, "2"),
    }


def compute_all_directional_overlaps(parsed_data):
    """
    Compute overlap quantities for x, y, and z directions.
    """
    molecules = build_all_molecules(parsed_data)

    x_atomic_overlap = compute_atomic_overlap_matrix(molecules["x1"], molecules["x2"])
    y_atomic_overlap = compute_atomic_overlap_matrix(molecules["y1"], molecules["y2"])
    z_atomic_overlap = compute_atomic_overlap_matrix(molecules["z1"], molecules["z2"])

    x_s_pm, x_alpha_det, x_beta_det = compute_mo_overlap_determinant(
        x_atomic_overlap,
        parsed_data["x1"]["alpha_coefficients"], parsed_data["x2"]["alpha_coefficients"],
        parsed_data["x1"]["beta_coefficients"], parsed_data["x2"]["beta_coefficients"]
    )

    y_s_pm, y_alpha_det, y_beta_det = compute_mo_overlap_determinant(
        y_atomic_overlap,
        parsed_data["y1"]["alpha_coefficients"], parsed_data["y2"]["alpha_coefficients"],
        parsed_data["y1"]["beta_coefficients"], parsed_data["y2"]["beta_coefficients"]
    )

    z_s_pm, z_alpha_det, z_beta_det = compute_mo_overlap_determinant(
        z_atomic_overlap,
        parsed_data["z1"]["alpha_coefficients"], parsed_data["z2"]["alpha_coefficients"],
        parsed_data["z1"]["beta_coefficients"], parsed_data["z2"]["beta_coefficients"]
    )

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


def calculate_denominator(ma_value, mn_value, step_value):
    """Compute the denominator in the final DBOC-related expression."""
    return (
        2
        * (ma_value * 1822.88847977884 - mn_value)
        * step_value ** 2
        * 1.88972612462577 ** 2
        / 219474.63
    )


def compute_final_result(parsed_data, ma, mn, step):
    """
    Compute the final result from parsed WFX data and user parameters.
    """
    overlap_results = compute_all_directional_overlaps(parsed_data)
    sum_value = 3 - overlap_results["x_s_pm"] - overlap_results["y_s_pm"] - overlap_results["z_s_pm"]
    denominator = calculate_denominator(ma, mn, step)
    result = sum_value / denominator / 2
    return overlap_results, sum_value, result