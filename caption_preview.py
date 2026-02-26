#!/usr/bin/env python3
"""
Modul pentru previzualizarea și validarea caption-urilor înainte de export
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
from typing import List, Dict
import difflib


class CaptionPreviewWindow:
    """Fereastră pentru previzualizarea și editarea caption-urilor"""

    def __init__(self, parent, captions: List[Dict], original_text: str = None):
        """
        Inițializează fereastra de previzualizare

        Args:
            parent: Fereastra părinte
            captions: Lista de captions pentru previzualizare
            original_text: Textul original pentru comparare (opțional)
        """
        self.parent = parent
        self.captions = captions.copy()  # Copie pentru a nu modifica originalul
        self.original_text = original_text
        self.approved = False

        # Creează fereastra
        self.window = tk.Toplevel(parent)
        self.window.title("🔍 Previzualizare și Validare Captions")
        self.window.geometry("900x700")
        self.window.minsize(800, 600)

        # Variables
        self.current_index = 0
        self.edited_captions = {}  # Stochează caption-urile editate

        self.setup_ui()
        self.load_caption(0)

        # Focus pe fereastră
        self.window.focus_set()
        self.window.grab_set()

    def setup_ui(self):
        """Configurează interfața de previzualizare"""
        # Main container
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="🔍 Previzualizare Captions",
                              font=('Segoe UI', 14, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10), sticky="w")

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        # Tab 1: Caption editor
        self.create_editor_tab()

        # Tab 2: Full list view
        self.create_list_tab()

        # Tab 3: Comparison view (if original text exists)
        if self.original_text:
            self.create_comparison_tab()

        # Bottom buttons
        self.create_buttons(main_frame)

    def create_editor_tab(self):
        """Creează tab-ul pentru editarea caption-urilor"""
        editor_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(editor_frame, text="✏️ Editor")

        editor_frame.columnconfigure(0, weight=1)

        # Navigation frame
        nav_frame = ttk.Frame(editor_frame)
        nav_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ttk.Button(nav_frame, text="◀ Anterior", command=self.prev_caption).grid(row=0, column=0, padx=(0, 5))

        self.caption_info = ttk.Label(nav_frame, text="", font=('Segoe UI', 10, 'bold'))
        self.caption_info.grid(row=0, column=1, padx=20)

        ttk.Button(nav_frame, text="Următor ▶", command=self.next_caption).grid(row=0, column=2, padx=(5, 0))

        # Caption details frame
        details_frame = ttk.LabelFrame(editor_frame, text="📝 Detalii Caption", padding=10)
        details_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        details_frame.columnconfigure(1, weight=1)

        # Timing info
        ttk.Label(details_frame, text="Start:").grid(row=0, column=0, sticky="w", pady=2)
        self.start_label = ttk.Label(details_frame, text="", font=('Consolas', 10))
        self.start_label.grid(row=0, column=1, sticky="w", pady=2, padx=(10, 0))

        ttk.Label(details_frame, text="Sfârșit:").grid(row=1, column=0, sticky="w", pady=2)
        self.end_label = ttk.Label(details_frame, text="", font=('Consolas', 10))
        self.end_label.grid(row=1, column=1, sticky="w", pady=2, padx=(10, 0))

        ttk.Label(details_frame, text="Durată:").grid(row=2, column=0, sticky="w", pady=2)
        self.duration_label = ttk.Label(details_frame, text="", font=('Consolas', 10))
        self.duration_label.grid(row=2, column=1, sticky="w", pady=2, padx=(10, 0))

        ttk.Label(details_frame, text="Cuvinte:").grid(row=3, column=0, sticky="w", pady=2)
        self.words_label = ttk.Label(details_frame, text="", font=('Consolas', 10))
        self.words_label.grid(row=3, column=1, sticky="w", pady=2, padx=(10, 0))

        # Text editor frame
        text_frame = ttk.LabelFrame(editor_frame, text="✏️ Text Caption", padding=10)
        text_frame.grid(row=2, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(2, weight=1)

        # Text widget for editing
        self.text_editor = tk.Text(text_frame, height=4, wrap=tk.WORD,
                                  font=('Segoe UI', 12), bg='#f8f9fa')
        self.text_editor.grid(row=0, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)

        # Bind text changes
        self.text_editor.bind('<KeyRelease>', self.on_text_change)

        # Action buttons for editor
        action_frame = ttk.Frame(text_frame)
        action_frame.grid(row=1, column=0, sticky="w", pady=(10, 0))

        ttk.Button(action_frame, text="💾 Salvează Modificarea",
                  command=self.save_current_edit).grid(row=0, column=0, padx=(0, 5))

        ttk.Button(action_frame, text="↩️ Resetează",
                  command=self.reset_current_caption).grid(row=0, column=1, padx=5)

        self.edit_status = ttk.Label(action_frame, text="", foreground='green')
        self.edit_status.grid(row=0, column=2, padx=(20, 0))

    def create_list_tab(self):
        """Creează tab-ul cu lista completă de captions"""
        list_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(list_frame, text="📋 Listă Completă")

        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Treeview pentru captions
        columns = ('ID', 'Start', 'Sfârșit', 'Durată', 'Text')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        # Configure columns
        self.tree.heading('ID', text='#')
        self.tree.heading('Start', text='Start')
        self.tree.heading('Sfârșit', text='Sfârșit')
        self.tree.heading('Durată', text='Durată')
        self.tree.heading('Text', text='Text')

        self.tree.column('ID', width=40, stretch=False)
        self.tree.column('Start', width=80, stretch=False)
        self.tree.column('Sfârșit', width=80, stretch=False)
        self.tree.column('Durată', width=80, stretch=False)
        self.tree.column('Text', width=400, stretch=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Populate tree
        self.populate_tree()

        # Bind double-click
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)

        # Stats frame
        stats_frame = ttk.Frame(list_frame)
        stats_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.stats_label = ttk.Label(stats_frame, text="", font=('Segoe UI', 10))
        self.stats_label.grid(row=0, column=0, sticky="w")

        self.update_stats()

    def create_comparison_tab(self):
        """Creează tab-ul pentru compararea cu textul original"""
        comp_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(comp_frame, text="🔍 Comparare")

        comp_frame.columnconfigure(0, weight=1)
        comp_frame.columnconfigure(1, weight=1)
        comp_frame.rowconfigure(1, weight=1)

        # Labels
        ttk.Label(comp_frame, text="📝 Text Original (ElevenLabs)",
                 font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, sticky="w", pady=(0, 5))

        ttk.Label(comp_frame, text="🎬 Text din Captions",
                 font=('Segoe UI', 11, 'bold')).grid(row=0, column=1, sticky="w", pady=(0, 5), padx=(10, 0))

        # Text areas
        orig_frame = ttk.Frame(comp_frame)
        orig_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        orig_frame.columnconfigure(0, weight=1)
        orig_frame.rowconfigure(0, weight=1)

        self.orig_text = tk.Text(orig_frame, wrap=tk.WORD, font=('Consolas', 10), bg='#e8f5e9')
        self.orig_text.grid(row=0, column=0, sticky="nsew")
        self.orig_text.insert('1.0', self.original_text or "")
        self.orig_text.config(state='disabled')

        orig_scroll = ttk.Scrollbar(orig_frame, orient='vertical', command=self.orig_text.yview)
        orig_scroll.grid(row=0, column=1, sticky="ns")
        self.orig_text.config(yscrollcommand=orig_scroll.set)

        capt_frame = ttk.Frame(comp_frame)
        capt_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        capt_frame.columnconfigure(0, weight=1)
        capt_frame.rowconfigure(0, weight=1)

        self.capt_text = tk.Text(capt_frame, wrap=tk.WORD, font=('Consolas', 10), bg='#fff3e0')
        self.capt_text.grid(row=0, column=0, sticky="nsew")

        capt_scroll = ttk.Scrollbar(capt_frame, orient='vertical', command=self.capt_text.yview)
        capt_scroll.grid(row=0, column=1, sticky="ns")
        self.capt_text.config(yscrollcommand=capt_scroll.set)

        # Populate captions text
        self.update_captions_text()

        # Highlight differences button
        diff_frame = ttk.Frame(comp_frame)
        diff_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        ttk.Button(diff_frame, text="🔍 Evidențiază Diferențele",
                  command=self.highlight_differences).grid(row=0, column=0)

        self.diff_label = ttk.Label(diff_frame, text="", font=('Segoe UI', 10))
        self.diff_label.grid(row=0, column=1, padx=(20, 0))

    def create_buttons(self, parent):
        """Creează butoanele principale"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        button_frame.columnconfigure(1, weight=1)

        # Left buttons
        left_frame = ttk.Frame(button_frame)
        left_frame.grid(row=0, column=0, sticky="w")

        ttk.Button(left_frame, text="✅ Aprobă și Continuă",
                  command=self.approve_and_close,
                  style='Success.TButton').grid(row=0, column=0, padx=(0, 5))

        ttk.Button(left_frame, text="❌ Anulează",
                  command=self.cancel).grid(row=0, column=1, padx=5)

        # Right buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.grid(row=0, column=2, sticky="e")

        ttk.Button(right_frame, text="💾 Salvează Modificările",
                  command=self.save_all_edits).grid(row=0, column=0, padx=(0, 5))

        ttk.Button(right_frame, text="↩️ Resetează Tot",
                  command=self.reset_all).grid(row=0, column=1)

    def load_caption(self, index):
        """Încarcă un caption în editor"""
        if 0 <= index < len(self.captions):
            self.current_index = index
            caption = self.get_caption(index)

            # Update navigation info
            self.caption_info.config(text=f"Caption {index + 1} din {len(self.captions)}")

            # Update timing info
            self.start_label.config(text=f"{caption['start']:.2f}s")
            self.end_label.config(text=f"{caption['end']:.2f}s")
            self.duration_label.config(text=f"{caption['end'] - caption['start']:.2f}s")
            self.words_label.config(text=str(len(caption['text'].split())))

            # Update text editor
            self.text_editor.delete('1.0', tk.END)
            self.text_editor.insert('1.0', caption['text'])

            # Clear edit status
            self.edit_status.config(text="")

    def get_caption(self, index):
        """Obține un caption (editat sau original)"""
        if index in self.edited_captions:
            return self.edited_captions[index]
        return self.captions[index]

    def prev_caption(self):
        """Navighează la caption-ul anterior"""
        if self.current_index > 0:
            self.load_caption(self.current_index - 1)

    def next_caption(self):
        """Navighează la caption-ul următor"""
        if self.current_index < len(self.captions) - 1:
            self.load_caption(self.current_index + 1)

    def on_text_change(self, event=None):
        """Handler pentru modificarea textului"""
        current_text = self.text_editor.get('1.0', tk.END).strip()
        original_text = self.captions[self.current_index]['text']

        if current_text != original_text:
            self.edit_status.config(text="✏️ Modificat", foreground='orange')
        else:
            self.edit_status.config(text="", foreground='green')

    def save_current_edit(self):
        """Salvează modificarea curentă"""
        new_text = self.text_editor.get('1.0', tk.END).strip()
        if new_text:
            caption = self.captions[self.current_index].copy()
            caption['text'] = new_text
            caption['was_edited'] = True
            self.edited_captions[self.current_index] = caption
            self.edit_status.config(text="✅ Salvat", foreground='green')
            self.populate_tree()
            self.update_captions_text()
            self.update_stats()

    def reset_current_caption(self):
        """Resetează caption-ul curent la original"""
        if self.current_index in self.edited_captions:
            del self.edited_captions[self.current_index]
        self.load_caption(self.current_index)
        self.populate_tree()
        self.update_captions_text()
        self.update_stats()

    def populate_tree(self):
        """Populează tree view cu captions"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add captions
        for i, caption in enumerate(self.captions):
            caption_data = self.get_caption(i)
            values = (
                i + 1,
                f"{caption_data['start']:.2f}s",
                f"{caption_data['end']:.2f}s",
                f"{caption_data['end'] - caption_data['start']:.2f}s",
                caption_data['text']
            )

            tags = []
            if i in self.edited_captions:
                tags.append('edited')

            self.tree.insert('', 'end', values=values, tags=tags)

        # Configure tag colors
        self.tree.tag_configure('edited', background='#fff3cd')

    def on_tree_double_click(self, event):
        """Handler pentru double-click pe tree"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            values = self.tree.item(item)['values']
            if values:
                index = values[0] - 1
                self.load_caption(index)
                self.notebook.select(0)  # Switch to editor tab

    def update_captions_text(self):
        """Actualizează textul complet din captions"""
        if hasattr(self, 'capt_text'):
            self.capt_text.config(state='normal')
            self.capt_text.delete('1.0', tk.END)

            full_text = []
            for i in range(len(self.captions)):
                caption = self.get_caption(i)
                full_text.append(caption['text'])

            self.capt_text.insert('1.0', ' '.join(full_text))
            self.capt_text.config(state='disabled')

    def update_stats(self):
        """Actualizează statisticile"""
        total = len(self.captions)
        edited = len(self.edited_captions)
        total_words = sum(len(self.get_caption(i)['text'].split()) for i in range(total))

        self.stats_label.config(text=f"📊 Total: {total} captions | {total_words} cuvinte | {edited} modificate")

    def highlight_differences(self):
        """Evidențiază diferențele între textul original și captions"""
        if not self.original_text:
            return

        # Get captions text
        captions_text = ' '.join(self.get_caption(i)['text'] for i in range(len(self.captions)))

        # Calculate similarity
        matcher = difflib.SequenceMatcher(None, self.original_text, captions_text)
        ratio = matcher.ratio()

        self.diff_label.config(text=f"Similaritate: {ratio*100:.1f}%")

        # Clear existing tags
        self.orig_text.tag_delete('diff')
        self.capt_text.tag_delete('diff')

        # Configure tags
        self.orig_text.tag_configure('diff', background='#ffcdd2')
        self.capt_text.tag_configure('diff', background='#ffcdd2')

        # Highlight differences
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                if tag in ['delete', 'replace']:
                    self.orig_text.config(state='normal')
                    start_idx = f"1.0 + {i1} chars"
                    end_idx = f"1.0 + {i2} chars"
                    self.orig_text.tag_add('diff', start_idx, end_idx)
                    self.orig_text.config(state='disabled')

                if tag in ['insert', 'replace']:
                    self.capt_text.config(state='normal')
                    start_idx = f"1.0 + {j1} chars"
                    end_idx = f"1.0 + {j2} chars"
                    self.capt_text.tag_add('diff', start_idx, end_idx)
                    self.capt_text.config(state='disabled')

    def save_all_edits(self):
        """Salvează toate modificările în captions originale"""
        count = len(self.edited_captions)
        if count > 0:
            # Apply edits to original captions
            for index, edited in self.edited_captions.items():
                self.captions[index] = edited
            messagebox.showinfo("Succes", f"✅ {count} modificări salvate!")
        else:
            messagebox.showinfo("Info", "Nu există modificări de salvat")

    def reset_all(self):
        """Resetează toate modificările"""
        if self.edited_captions:
            result = messagebox.askyesno("Confirmare",
                                        f"Sigur vrei să resetezi toate cele {len(self.edited_captions)} modificări?")
            if result:
                self.edited_captions.clear()
                self.load_caption(self.current_index)
                self.populate_tree()
                self.update_captions_text()
                self.update_stats()
                messagebox.showinfo("Resetat", "Toate modificările au fost anulate")

    def approve_and_close(self):
        """Aprobă captions și închide fereastra"""
        # Apply all edits
        for index, edited in self.edited_captions.items():
            self.captions[index] = edited

        self.approved = True
        self.window.destroy()

    def cancel(self):
        """Anulează și închide fereastra"""
        if self.edited_captions:
            result = messagebox.askyesno("Confirmare",
                                        "Ai modificări nesalvate. Sigur vrei să anulezi?")
            if not result:
                return

        self.approved = False
        self.window.destroy()

    def get_final_captions(self):
        """Returnează captions finale (cu modificări aplicate)"""
        return self.captions if self.approved else None