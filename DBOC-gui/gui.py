import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import tkinter.font as tkfont
import threading
import time

from wfx_parser import parse_files
from overlap_calc import compute_final_result


class DBOCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DBOC Calculation")
        self.root.geometry("900x650")

        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=9)
        self.root.option_add("*Font", default_font)

        self.file_paths = []
        self.file_map = {}
        self.calculation_in_progress = False

        self.progress_var = tk.DoubleVar()
        self._build_widgets()

    def _build_widgets(self):
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(pady=5, fill=tk.X, padx=20)
        self.progress_bar.pack_forget()

        self.status_label = tk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        self.select_btn = tk.Button(self.root, text="Select 6 WFX Files", command=self.select_files)
        self.select_btn.pack(pady=10)

        param_frame = tk.Frame(self.root)
        param_frame.pack(pady=10)

        tk.Label(param_frame, text="Ma:").grid(row=0, column=0, padx=5)
        self.ma_entry = tk.Entry(param_frame, width=12)
        self.ma_entry.grid(row=0, column=1, padx=5)

        tk.Label(param_frame, text="Mn:").grid(row=0, column=2, padx=5)
        self.mn_entry = tk.Entry(param_frame, width=12)
        self.mn_entry.grid(row=0, column=3, padx=5)

        tk.Label(param_frame, text="Step:").grid(row=0, column=4, padx=5)
        self.step_entry = tk.Entry(param_frame, width=12)
        self.step_entry.grid(row=0, column=5, padx=5)
        self.step_entry.insert(0, "0.001")

        self.calc_btn = tk.Button(self.root, text="Start Calculation", command=self.start_calculation)
        self.calc_btn.pack(pady=10)

        self.result_text = scrolledtext.ScrolledText(self.root, width=100, height=24)
        self.result_text.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

    def update_progress(self, step, total_steps=100):
        progress = (step / total_steps) * 100
        self.progress_var.set(progress)
        self.root.update_idletasks()

    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def show_result(self, text):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        self.root.update_idletasks()

    def assign_files(self):
        file_map = {
            "x1": "", "x2": "",
            "y1": "", "y2": "",
            "z1": "", "z2": ""
        }

        for path in self.file_paths:
            filename = path.split("\\")[-1] if "\\" in path else path.split("/")[-1]

            import re
            if re.search(r"\+x\d+\.\d+", filename):
                file_map["x1"] = path
            elif re.search(r"\-x\d+\.\d+", filename):
                file_map["x2"] = path
            elif re.search(r"\+y\d+\.\d+", filename):
                file_map["y1"] = path
            elif re.search(r"\-y\d+\.\d+", filename):
                file_map["y2"] = path
            elif re.search(r"\+z\d+\.\d+", filename):
                file_map["z1"] = path
            elif re.search(r"\-z\d+\.\d+", filename):
                file_map["z2"] = path

        self.file_map = file_map

        if all(file_map.values()):
            self.show_result("File assignment successful.\nClick 'Start Calculation' to proceed.")
        else:
            self.show_result(
                "File naming pattern not recognized.\n"
                "Please ensure filenames contain +x/-x/+y/-y/+z/-z labels."
            )

    def validate_assigned_files(self):
        return bool(self.file_map) and all(self.file_map.values())

    def select_files(self):
        if self.calculation_in_progress:
            self.show_result("Please wait until the current calculation is finished.")
            return

        files = filedialog.askopenfilenames(
            title="Select 6 WFX files",
            filetypes=[("WFX files", "*.wfx"), ("All files", "*.*")]
        )

        if len(files) != 6:
            self.show_result("Please select exactly 6 files.")
            return

        self.file_paths = list(files)
        self.assign_files()

        self.show_result("Selected 6 files:\n" + "\n".join(self.file_paths))

    def read_parameters(self):
        ma = float(self.ma_entry.get())
        mn = float(self.mn_entry.get())
        step = float(self.step_entry.get())
        return ma, mn, step

    def format_final_output(self, overlap_results, result, sum_value, run_time):
        selected_files_text = "Selected 6 files:\n" + "\n".join(self.file_paths)

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

    def run_calculation_pipeline(self):
        start_time = time.time()
        self.update_status("Initializing calculation...")
        self.show_result("Selected 6 files:\n" + "\n".join(self.file_paths) + "\n\nCalculation in progress...\n")
        self.update_progress(5)

        if not self.validate_assigned_files():
            self.show_result("Please select and assign all six files correctly before calculation.")
            return

        self.update_status("Parsing WFX files...")
        parsed_data = parse_files(self.file_map)
        self.update_progress(50)

        try:
            ma, mn, step = self.read_parameters()
        except ValueError:
            self.show_result("Please enter valid values for Ma, Mn, and Step.")
            return

        self.update_status("Computing overlap integrals...")
        overlap_results, sum_value, result = compute_final_result(parsed_data, ma, mn, step)
        self.update_progress(95)

        run_time = time.time() - start_time
        final_output = self.format_final_output(overlap_results, result, sum_value, run_time)

        self.show_result(final_output)
        self.update_progress(100)
        self.update_status("Calculation completed")

    def calculation_thread(self):
        try:
            self.calculation_in_progress = True
            self.select_btn.config(state=tk.DISABLED)
            self.calc_btn.config(state=tk.DISABLED)
            self.progress_bar.pack(pady=5, fill=tk.X, padx=20)

            self.run_calculation_pipeline()

        except Exception as e:
            self.show_result(f"An error occurred during calculation: {str(e)}")
        finally:
            self.calculation_in_progress = False
            self.select_btn.config(state=tk.NORMAL)
            self.calc_btn.config(state=tk.NORMAL)
            self.progress_bar.pack_forget()
            self.progress_var.set(0)

    def start_calculation(self):
        if self.calculation_in_progress:
            self.show_result("A calculation is already in progress. Please wait.")
            return

        if not self.validate_assigned_files():
            self.show_result("Please select and assign all six files correctly first.")
            return

        thread = threading.Thread(target=self.calculation_thread)
        thread.daemon = True
        thread.start()


def run_app():
    root = tk.Tk()
    app = DBOCApp(root)
    root.mainloop()