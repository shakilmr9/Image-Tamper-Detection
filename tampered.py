import numpy as np
import tkinter as tk
import cv2
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter import Button, filedialog, messagebox, Label
from PIL import Image, ImageTk
import hashlib
import mysql.connector
import io

class ImageTamperApp:
    def __init__(self, root, return_to_main_ui, user_id):
        self.root = root
        self.return_to_main_ui = return_to_main_ui
        self.user_id = user_id
        self.original_image_path = None
        self.tampered_image_path = None
        
        self.setup_ui()
        
    def setup_ui(self):
        self.root.title("Image Tamper Detection")
        self.root.geometry("1000x700")
        self.root.configure(bg="#2b2a2a")

        # Button frame
        self.button_frame = tk.Frame(self.root, bg="#2b2a2a")
        self.button_frame.pack(pady=10)

        self.original_button = Button(self.button_frame, text="Input Original Photo", 
                                    command=self.load_original_image, bg="#4CAF50", 
                                    fg="white", font=("Roboto", 10))
        self.original_button.pack(side="left", padx=10, pady=5)

        self.tampered_button = Button(self.button_frame, text="Input Tampered Photo", 
                                     command=self.load_tampered_image, bg="#4CAF50", 
                                     fg="white", font=("Roboto", 10))
        self.tampered_button.pack(side="left", padx=10, pady=5)

        self.detect_button = Button(self.button_frame, text="Detect Tampering", 
                                   command=self.detect_tampering, bg="#4CAF50", 
                                   fg="white", font=("Roboto", 10))
        self.detect_button.pack(side="left", padx=10, pady=5)

        self.save_pdf_button = Button(self.button_frame, text="Save Output as PDF", 
                                     command=self.save_output_as_pdf, bg="#4CAF50", 
                                     fg="white", font=("Roboto", 10))
        self.save_pdf_button.pack(side="left", padx=10, pady=5)

        self.back_button = Button(self.root, text="Back", command=self.go_back, 
                                bg="#FF0000", fg="white", font=("Roboto", 10))
        self.back_button.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

        # Image display frames
        self.image_frame = tk.Frame(self.root, bg="#2b2a2a")
        self.image_frame.pack(pady=20)

        self.setup_image_display(self.image_frame, "Original Image", 0)
        self.setup_image_display(self.image_frame, "Tampered Image", 1)
        self.setup_image_display(self.image_frame, "Difference Mask", 2)

        # Histogram frames
        self.histogram_frame = tk.Frame(self.root, bg="#2b2a2a")
        self.histogram_frame.pack(pady=20)

        self.setup_histogram_display(self.histogram_frame, "Original Histogram", 0)
        self.setup_histogram_display(self.histogram_frame, "Tampered Histogram", 1)
        self.setup_histogram_display(self.histogram_frame, "Difference Histogram", 2)

    def setup_image_display(self, parent, title, column):
        frame = tk.Frame(parent, width=300, height=200, bg="white")
        frame.grid(row=0, column=column, padx=10, pady=10)
        label = Label(frame, bg="white")
        label.pack()
        setattr(self, f"{title.lower().replace(' ', '_')}_label", label)
        
        title_label = Label(parent, text=title, fg="white", bg="#2b2a2a", 
                          font=("Lato", 12, "bold"))
        title_label.grid(row=1, column=column, pady=5)

    def setup_histogram_display(self, parent, title, column):
        frame = tk.Frame(parent, width=300, height=200, bg="white")
        frame.grid(row=0, column=column, padx=10, pady=10)
        label = Label(frame, bg="white")
        label.pack()
        setattr(self, f"{title.lower().replace(' ', '_')}_label", label)
        
        title_label = Label(parent, text=title, fg="white", bg="#2b2a2a", 
                          font=("Lato", 12, "bold"))
        title_label.grid(row=1, column=column, pady=5)

    def load_original_image(self):
        self.original_image_path = self.load_image("Select Original Image")
        if self.original_image_path:
            self.display_image(self.original_image_label, self.original_image_path)

    def load_tampered_image(self):
        self.tampered_image_path = self.load_image("Select Tampered Image")
        if self.tampered_image_path:
            self.display_image(self.tampered_image_label, self.tampered_image_path)

    def load_image(self, title):
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.gif")]
        )
        if file_path:
            messagebox.showinfo("Success", f"{title.split()[-1]} image loaded successfully!")
            return file_path
        return None

    def detect_tampering(self):
        if self.original_image_path and self.tampered_image_path:
            self.detect_tampering_logic()
        else:
            messagebox.showerror("Error", "Please load both original and tampered images!")

    def save_output_as_pdf(self):
        if self.original_image_path and self.tampered_image_path:
            self.detect_tampering_logic(save_pdf=True)
        else:
            messagebox.showerror("Error", "Please load both original and tampered images!")

    def compute_image_hash(self, image_path):
        image = Image.open(image_path)
        image_array = np.array(image)
        if image_array.dtype != np.uint8:
            image_array = image_array.astype(np.uint8)
        flattened_array = image_array.flatten(order='C')
        return hashlib.sha1(flattened_array.tobytes()).hexdigest()

    def detect_tampering_logic(self, save_pdf=False):
        try:
            threshold = 10

            original_hash = self.compute_image_hash(self.original_image_path)
            tampered_hash = self.compute_image_hash(self.tampered_image_path)

            if original_hash == tampered_hash:
                messagebox.showinfo("Result", "No tampering detected. The images are identical.")
                return

            original = Image.open(self.original_image_path).convert('L') 
            tampered = Image.open(self.tampered_image_path).convert('L') 

            original = np.array(original)
            tampered = np.array(tampered)

            if original.shape != tampered.shape:
                tampered = cv2.resize(tampered, (original.shape[1], original.shape[0]))

            diff = cv2.absdiff(original, tampered)
            _, mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

            self.display_image(self.difference_mask_label, mask)
            self.display_histogram(self.original_histogram_label, original, "Original Image Histogram")
            self.display_histogram(self.tampered_histogram_label, tampered, "Tampered Image Histogram")
            self.display_histogram(self.difference_histogram_label, mask, "Difference Mask Histogram")

            if save_pdf:
                pdf_path = filedialog.asksaveasfilename(defaultextension=".pdf", 
                                                      filetypes=[("PDF Files", "*.pdf")])
                if pdf_path:
                    self.save_output_to_pdf(original, tampered, mask, pdf_path)
                    self.save_image_to_database(mask)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def display_image(self, label, image):
        if isinstance(image, str):
            image = Image.open(image)
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        image = image.resize((300, 200), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        label.config(image=photo)
        label.image = photo

    def display_histogram(self, label, image, title):
        fig = Figure(figsize=(3, 2), dpi=100)
        ax = fig.add_subplot(111)
        ax.hist(image.ravel(), bins=256, range=(0, 256), color='black', alpha=0.75)
        ax.set_title(title)
        ax.set_xlabel("Pixel Intensity")
        ax.set_ylabel("Frequency")

        canvas = FigureCanvasTkAgg(fig, master=label)
        canvas.draw()
        canvas.get_tk_widget().pack()

    def save_output_to_pdf(self, original, tampered, mask, pdf_path):
        fig = plt.figure(figsize=(15, 10))

        plt.subplot(2, 3, 1)
        plt.imshow(original, cmap='gray')
        plt.title('Original Image')
        plt.axis('off')

        plt.subplot(2, 3, 2)
        plt.imshow(tampered, cmap='gray')
        plt.title('Tampered Image')
        plt.axis('off')

        plt.subplot(2, 3, 3)
        plt.imshow(mask, cmap='gray')
        plt.title('Difference Mask')
        plt.axis('off')

        plt.subplot(2, 3, 4)
        plt.hist(original.ravel(), bins=256, range=(0, 256), color='black', alpha=0.75)
        plt.title('Original Image Histogram')
        plt.xlabel('Pixel Intensity')
        plt.ylabel('Frequency')

        plt.subplot(2, 3, 5)
        plt.hist(tampered.ravel(), bins=256, range=(0, 256), color='black', alpha=0.75)
        plt.title('Tampered Image Histogram')
        plt.xlabel('Pixel Intensity')
        plt.ylabel('Frequency')

        plt.subplot(2, 3, 6)
        plt.hist(mask.ravel(), bins=256, range=(0, 256), color='black', alpha=0.75)
        plt.title('Difference Mask Histogram')
        plt.xlabel('Pixel Intensity')
        plt.ylabel('Frequency')

        plt.tight_layout()
        plt.savefig(pdf_path)
        plt.close()
        messagebox.showinfo("Success", f"Output saved as {pdf_path}")

    def save_image_to_database(self, image):
        try:
            img_byte_arr = io.BytesIO()
            Image.fromarray(image).save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            conn = mysql.connector.connect(
                host='localhost', user='root', port='3306', 
                password='Shakil@420', database='py_lg_rg_db'
            )
            cursor = conn.cursor()

            query = "INSERT INTO images (image_data, user_id) VALUES (%s, %s)"
            cursor.execute(query, (img_byte_arr, self.user_id))
            conn.commit()

            messagebox.showinfo("Success", "Difference mask image saved to database!")

        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Failed to save image to database: {err}")
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    def go_back(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.return_to_main_ui()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageTamperApp(root, lambda: None, user_id=1)
    root.mainloop()