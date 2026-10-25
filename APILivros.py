import json
import tkinter as tk

import requests

API_URL = "https://openlibrary.org/search.json"
HISTORY_FILE = "Historico.json"


class BookSearchApp:
    def __init__(self, root):
        self.root = root
        self.press_counter = 0
        self.main_frame = None
        self.build_main_screen()

    def _default_history(self):
        return {
            "History": [{"name": None}],
            "Presented": [{"name": None}],
            "Favorites": [{"name": None}],
        }

    def _load_history(self):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = self._default_history()

        if not isinstance(data, dict):
            data = self._default_history()

        for old_key, new_key in {
            "Historico": "History",
            "Apresentados": "Presented",
            "Favoritos": "Favorites",
        }.items():
            if old_key in data and new_key not in data:
                data[new_key] = data.pop(old_key)

        for key in ("History", "Presented", "Favorites"):
            data.setdefault(key, [])
            if not isinstance(data[key], list):
                data[key] = []

        return data

    def _save_history(self, data):
        with open(HISTORY_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def _ensure_history(self):
        data = self._load_history()
        for key in ("History", "Presented", "Favorites"):
            if not data.get(key):
                data[key] = [{"name": None}]
        self._save_history(data)
        return data

    def _clear_frame(self):
        if self.main_frame is not None:
            self.main_frame.destroy()
        self.main_frame = None

    def _show_text(self, text):
        if hasattr(self, "result_box"):
            self.result_box.delete("1.0", tk.END)
            self.result_box.insert(tk.END, text)

    def build_main_screen(self):
        self._clear_frame()
        self.main_frame = tk.Frame(self.root, bg="black", width=550, height=590)
        self.main_frame.grid()
        self.main_frame.grid_propagate(False)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.title_label = tk.Label(self.main_frame, text="Book:")
        self.title_label.grid(row=0, column=0, pady=10, padx=100, sticky="w")

        self.author_label = tk.Label(self.main_frame, text="Author:")
        self.author_label.grid(row=0, column=0, pady=10, padx=185, sticky="e")

        self.title_entry = tk.Entry(self.main_frame)
        self.title_entry.grid(row=1, column=0, pady=10, padx=100, sticky="w")

        self.author_entry = tk.Entry(self.main_frame)
        self.author_entry.grid(row=1, column=0, pady=10, padx=100, sticky="e")

        self.search_book_button = tk.Button(self.main_frame, text="Search book", command=self.search_book)
        self.search_book_button.grid(row=2, column=0, pady=20, padx=60, sticky="w")

        self.search_author_button = tk.Button(self.main_frame, text="Search author", command=self.search_author)
        self.search_author_button.grid(row=2, column=0, pady=20, padx=170, sticky="w")

        self.history_button = tk.Button(self.main_frame, text="Open history", command=self.open_history)
        self.history_button.grid(row=2, column=0, pady=20, padx=170, sticky="e")

        self.favorite_button = tk.Button(self.main_frame, text="Open favorites", command=self.open_favorites_screen)
        self.favorite_button.grid(row=2, column=0, pady=20, padx=50, sticky="e")

        self.result_box = tk.Text(self.main_frame, bg="white")
        self.result_box.grid(row=3, column=0, pady=20, padx=20, sticky="")

    def get_user_input(self):
        try:
            title = self.title_entry.get().strip()
            author = self.author_entry.get().strip()
        except AttributeError:
            title = ""
            author = ""
        return title, author

    def request_books(self, title="", author=""):
        params = {}
        if title:
            params["title"] = title
        if author:
            params["author_name"] = author
            params["author"] = author

        try:
            return requests.get(API_URL, params=params, timeout=10)
        except requests.RequestException:
            return None

    def validate_request(self):
        title, author = self.get_user_input()
        response = self.request_books(title, author)
        if response is None:
            self._show_text("It was not possible to access the API!")
            return None

        if response.status_code != 200:
            self._show_text(f"Request failed with error: {response.status_code}\n")
            return None

        self._ensure_history()
        return title, author, response

    def set_presented_results(self, items):
        data = self._load_history()

        if data.get("History") and data["History"][0].get("name") is None:
            data["History"] = []
        if data.get("Presented") and data["Presented"][0].get("name") is None:
            data["Presented"] = []

        clean_items = [item for item in items if item]
        data["Presented"] = [{"name": item} for item in clean_items]
        data["History"].extend({"name": item} for item in clean_items)
        self._save_history(data)

    def search_book(self):
        result = self.validate_request()
        if result is None:
            return

        title, _, response = result
        data = response.json()
        docs = data.get("docs", [])

        if not title:
            self._show_text("You must enter a value in the book field to search for books.")
            return

        matches = [doc.get("title", "") for doc in docs if title.lower() in str(doc.get("title", "")).lower()]
        if not matches:
            self._show_text("Book not found.")
            return

        self.set_presented_results(matches)
        self._show_text("\n".join(matches))

    def search_author(self):
        result = self.validate_request()
        if result is None:
            return

        _, author, response = result
        data = response.json()
        docs = data.get("docs", [])

        if not author:
            self._show_text("You must enter an author name, or search by book first and then by author.")
            return

        matches = []
        for doc in docs:
            author_names = doc.get("author_name", [])
            author_list = author_names if isinstance(author_names, list) else [str(author_names)]
            for name in author_list:
                if author.lower() in str(name).lower():
                    title = doc.get("title", "")
                    matches.append(f"{title} - {', '.join(author_list)}")
                    break

        if not matches:
            self._show_text("Author not found.")
            return

        self.set_presented_results(matches)
        self._show_text("\n".join(matches))

    def open_history(self):
        self._ensure_history()
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self._show_text("History is empty. Please search for something before viewing the history.")
            return

        items = [entry.get("name") for entry in data.get("History", []) if entry.get("name") is not None]
        if not items:
            self._show_text("History is empty. Please search for something before viewing the history.")
            return

        self._show_text("\n".join(items))

    def open_favorites_screen(self):
        self._clear_frame()
        self.main_frame = tk.Frame(self.root, bg="black", width=550, height=600)
        self.main_frame.grid()
        self.main_frame.grid_propagate(False)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.index_label = tk.Label(self.main_frame, text="Index:")
        self.index_label.grid(row=0, column=0, pady=10, padx=185, sticky="e")

        self.index_entry = tk.Entry(self.main_frame)
        self.index_entry.grid(row=1, column=0, pady=10, padx=100, sticky="e")

        self.remove_favorite_button = tk.Button(self.main_frame, text="Remove favorite", command=self.remove_favorite)
        self.remove_favorite_button.grid(row=2, column=0, pady=10, padx=60, sticky="w")

        self.add_from_history_button = tk.Button(self.main_frame, text="Add favorite from history", command=self.add_favorite_from_history)
        self.add_from_history_button.grid(row=2, column=0, pady=10, padx=60, sticky="e")

        self.result_box = tk.Text(self.main_frame, bg="white")
        self.result_box.grid(row=4, column=0, pady=10, padx=20, sticky="")

        self.back_button = tk.Button(self.main_frame, text="Back...", command=self.build_main_screen)
        self.back_button.grid(row=5, column=0, pady=20)

        self._ensure_history()
        self.display_favorites()

    def display_favorites(self):
        data = self._load_history()
        favorites = [f"{index} - {item.get('name')}" for index, item in enumerate(data.get("Favorites", [])) if item.get("name") is not None]
        self._show_text("\n".join(favorites) if favorites else "Your favorites list is empty.")

    def add_favorite_from_history(self):
        data = self._load_history()
        presented = data.get("Presented", [])
        if not presented or (len(presented) == 1 and presented[0].get("name") is None):
            self._show_text("Search first!")
            self.press_counter = 0
            return

        if self.press_counter == 0:
            self.press_counter = 1
            self._show_text("Select an index and click again to save it to favorites.\n")
            return

        index_text = self.index_entry.get().strip()
        if not index_text:
            self.press_counter = 0
            self._show_text("Choose one of the books by entering the matching index and click again.\n")
            return

        try:
            index = int(index_text)
            selected = presented[index]
        except (ValueError, IndexError):
            self.press_counter = 0
            self._show_text("Choose a valid value from the list.\n")
            return

        if selected.get("name") is None:
            self.press_counter = 0
            self._show_text("Choose a valid value from the list.\n")
            return

        if data.get("Favorites") and data["Favorites"][0].get("name") is None:
            data["Favorites"] = []

        favorite = {"name": selected["name"]}
        if favorite not in data["Favorites"]:
            data["Favorites"].append(favorite)
            self._show_text("Book added to favorites!\n")
        else:
            self._show_text("Book already added!\n")

        self.press_counter = 0
        self._save_history(data)
        self.display_favorites()

    def remove_favorite(self):
        data = self._load_history()
        favorites = data.get("Favorites", [])
        if not favorites or (len(favorites) == 1 and favorites[0].get("name") is None):
            self._show_text("You do not have any saved books yet!")
            self.press_counter = 0
            return

        if self.press_counter == 0:
            self.press_counter = 1
            self._show_text("Select the favorite index and click again to remove it.\n")
            return

        index_text = self.index_entry.get().strip()
        if not index_text:
            self.press_counter = 0
            self._show_text("Choose one of the books by entering the matching index and click again.\n")
            return

        try:
            index = int(index_text)
            if index >= len(favorites):
                raise ValueError
        except ValueError:
            self.press_counter = 0
            self._show_text("Choose a valid value from the list.\n")
            return

        favorites.pop(index)
        if not favorites:
            favorites = [{"name": None}]
        data["Favorites"] = favorites
        self.press_counter = 0
        self._save_history(data)
        self.display_favorites()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("550x600")
    root.title("Book Search")
    app = BookSearchApp(root)
    root.mainloop()
