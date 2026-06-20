"""Primitive Tkinter GUI for local DwC-A conversion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import queue
import subprocess
import threading
from typing import Any

from dwca_cloud_geospatial.conversion import (
    FLATGEOBUF_FORMAT,
    GEOPARQUET_FORMAT,
    ConversionError,
    ConversionOptions,
    ConversionResult,
    convert_dwca_archive,
)
from dwca_cloud_geospatial.geoparquet import GeoParquetWriterOptions
from dwca_cloud_geospatial.validation import BundleValidationResult, validate_output_bundle


DEFAULT_CHUNK_SIZE = 10_000


@dataclass(frozen=True)
class GuiConversionRequest:
    """Display-independent conversion request collected from GUI controls."""

    input_path: Path
    output_directory: Path
    output_formats: tuple[str, ...]
    overwrite: bool = False
    validate_after_conversion: bool = True
    geoparquet_large_output_mode: bool = False
    chunk_size: int = DEFAULT_CHUNK_SIZE


def selected_output_formats(
    *,
    flatgeobuf: bool,
    geoparquet: bool,
) -> tuple[str, ...]:
    """Return selected output formats in CLI-compatible order."""

    formats: list[str] = []
    if flatgeobuf:
        formats.append(FLATGEOBUF_FORMAT)
    if geoparquet:
        formats.append(GEOPARQUET_FORMAT)
    if not formats:
        raise ValueError("Select at least one output format.")
    return tuple(formats)


def parse_chunk_size(value: str) -> int:
    """Parse and validate a positive conversion chunk size."""

    try:
        chunk_size = int(value.strip())
    except ValueError as exc:
        raise ValueError("Chunk size must be a positive integer.") from exc
    if chunk_size <= 0:
        raise ValueError("Chunk size must be a positive integer.")
    return chunk_size


def validate_conversion_request(request: GuiConversionRequest) -> None:
    """Validate GUI request fields before starting conversion."""

    if not request.input_path.exists():
        raise ValueError(f"Input archive does not exist: {request.input_path}")
    if not request.input_path.is_file() and not request.input_path.is_dir():
        raise ValueError(f"Input archive must be a file or directory: {request.input_path}")
    if not request.output_directory.name:
        raise ValueError("Choose an output bundle directory.")
    parent = request.output_directory.parent
    if not parent.exists():
        raise ValueError(f"Output parent directory does not exist: {parent}")
    if request.output_directory.exists() and not request.overwrite:
        raise ValueError(
            "Output path already exists. Select the overwrite checkbox before "
            f"replacing {request.output_directory}."
        )
    if (
        request.geoparquet_large_output_mode
        and GEOPARQUET_FORMAT not in request.output_formats
    ):
        raise ValueError("GeoParquet large-output mode requires GeoParquet output.")


def build_conversion_options(request: GuiConversionRequest) -> ConversionOptions:
    """Build core conversion options without duplicating conversion behavior."""

    validate_conversion_request(request)
    return ConversionOptions(
        output_formats=request.output_formats,
        overwrite=request.overwrite,
        geoparquet=GeoParquetWriterOptions(
            large_output_mode=request.geoparquet_large_output_mode,
        ),
        chunk_size=request.chunk_size,
    )


def conversion_warning_lines(result: Any) -> list[str]:
    """Return human-readable non-fatal conversion warning lines."""

    lines: list[str] = []
    normalization_result = getattr(result, "normalization_result", None)
    for warning in getattr(normalization_result, "warnings", ()) or ():
        code = getattr(warning, "code", "warning")
        message = getattr(warning, "message", str(warning))
        lines.append(f"{code}: {message}")

    flatgeobuf_result = getattr(result, "flatgeobuf_result", None)
    for warning in getattr(flatgeobuf_result, "warnings", ()) or ():
        code = getattr(warning, "code", "warning")
        message = getattr(warning, "message", str(warning))
        details = []
        feature_count = getattr(warning, "feature_count", None)
        estimated_bytes = getattr(warning, "estimated_spatial_index_bytes", None)
        if feature_count is not None:
            details.append(f"features={feature_count}")
        if estimated_bytes is not None:
            details.append(f"estimated_spatial_index_bytes={estimated_bytes}")
        suffix = f" ({', '.join(details)})" if details else ""
        lines.append(f"{code}: {message}{suffix}")
    return lines


def format_conversion_summary(result: Any) -> str:
    """Format a conversion result for the GUI status panel."""

    lines = [
        f"Converted: {result.input_path} -> {result.output_directory}",
        f"Formats: {', '.join(result.output_formats)}",
        f"Accepted records: {result.accepted_record_count}",
        f"Rejected records: {result.rejected_record_count}",
        f"Manifest: {result.metadata_result.manifest_path}",
        f"Viewer entry: {result.output_directory / 'index.html'}",
    ]

    flatgeobuf_result = getattr(result, "flatgeobuf_result", None)
    if flatgeobuf_result is not None:
        lines.append(f"FlatGeobuf map source: {flatgeobuf_result.path}")
        staging_result = getattr(flatgeobuf_result, "staging_result", None)
        if staging_result is not None:
            lines.append(
                "GeoPackage staging artifact: "
                f"{staging_result.path} (retained for artifact/download metadata)"
            )

    geoparquet_result = getattr(result, "geoparquet_result", None)
    if geoparquet_result is not None:
        lines.append(f"GeoParquet artifact: {geoparquet_result.path}")
        if getattr(geoparquet_result, "large_output_mode", False):
            strategy = getattr(geoparquet_result, "spatial_sort_strategy", None)
            lines.append(
                "GeoParquet large-output mode: enabled"
                f"{f' ({strategy} spatial sort)' if strategy else ''}"
            )

    warnings = conversion_warning_lines(result)
    if warnings:
        lines.append("")
        lines.append("Non-fatal conversion warnings:")
        lines.extend(f"- {line}" for line in warnings)

    return "\n".join(lines)


def format_validation_summary(result: BundleValidationResult) -> str:
    """Format validation results with errors, warnings and skips separated."""

    lines = [
        f"Validation status: {result.status}",
        f"Required validation errors: {len(result.errors)}",
    ]
    if result.errors:
        for issue in result.errors:
            path = f" ({issue.path})" if issue.path else ""
            lines.append(f"- {issue.code}: {issue.message}{path}")
    else:
        lines.append("- None")

    lines.append(f"Validation warnings: {len(result.warnings)}")
    if result.warnings:
        for issue in result.warnings:
            path = f" ({issue.path})" if issue.path else ""
            lines.append(f"- {issue.code}: {issue.message}{path}")
    else:
        lines.append("- None")

    skipped = result.skipped_checks
    lines.append(f"Dependency-dependent skipped checks: {len(skipped)}")
    if skipped:
        for check in skipped:
            path = f" ({check.path})" if check.path else ""
            message = f": {check.message}" if check.message else ""
            lines.append(f"- {check.name}{path}{message}")
    else:
        lines.append("- None")

    return "\n".join(lines)


def viewer_instructions(result: Any) -> str:
    """Return viewer guidance for a generated bundle."""

    output = Path(result.output_directory)
    parent = output.parent
    local_url = f"http://localhost:8000/{output.name}/index.html"
    has_flatgeobuf = getattr(result, "flatgeobuf_result", None) is not None

    lines = [
        "Viewer instructions:",
        f"1. Serve the output parent: python -m http.server 8000 --directory {parent}",
        f"2. Open the copied viewer: {local_url}",
    ]
    if has_flatgeobuf:
        lines.append(
            "This bundle has a FlatGeobuf map layer at data/occurrences.fgb. "
            "Any data/occurrences.gpkg file is a retained artifact, not the MVP "
            "browser map source."
        )
    else:
        lines.append(
            "This GeoParquet-only bundle is valid. The copied viewer opens "
            "metadata, provenance, counts and artifact inventory, but it has no "
            "MVP browser map layer because no FlatGeobuf layer was generated."
        )
    lines.append(
        "The static viewer uses CDN-hosted MapLibre GL JS and FlatGeobuf JavaScript "
        "plus OpenStreetMap raster tiles; the Python GUI does not start a backend."
    )
    return "\n".join(lines)


class _ConverterGui:
    def __init__(self, tk: Any, ttk: Any, filedialog: Any, messagebox: Any) -> None:
        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.root = tk.Tk()
        self.root.title("DwC-A Cloud Geospatial Converter")
        self.root.geometry("920x680")

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.flatgeobuf_var = tk.BooleanVar(value=True)
        self.geoparquet_var = tk.BooleanVar(value=False)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.validate_var = tk.BooleanVar(value=True)
        self.large_geoparquet_var = tk.BooleanVar(value=False)
        self.chunk_size_var = tk.StringVar(value=str(DEFAULT_CHUNK_SIZE))

        self._queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._last_result: ConversionResult | None = None
        self._status_context_menu: Any | None = None

        self._build_widgets()

    def _build_widgets(self) -> None:
        root = self.root
        ttk = self.ttk
        tk = self.tk

        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        inputs = ttk.Frame(root, padding=12)
        inputs.grid(row=0, column=0, sticky="ew")
        inputs.columnconfigure(1, weight=1)

        ttk.Label(inputs, text="Input DwC-A archive or directory").grid(
            row=0, column=0, sticky="w", pady=4
        )
        ttk.Entry(inputs, textvariable=self.input_var).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(inputs, text="Browse...", command=self._choose_input).grid(
            row=0, column=2, sticky="ew"
        )

        ttk.Label(inputs, text="Output bundle directory").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Entry(inputs, textvariable=self.output_var).grid(
            row=1, column=1, sticky="ew", padx=8
        )
        ttk.Button(inputs, text="Browse...", command=self._choose_output).grid(
            row=1, column=2, sticky="ew"
        )

        options = ttk.LabelFrame(root, text="Options", padding=12)
        options.grid(row=1, column=0, sticky="ew", padx=12)
        for column in range(4):
            options.columnconfigure(column, weight=1)

        ttk.Checkbutton(
            options,
            text="FlatGeobuf (default map layer)",
            variable=self.flatgeobuf_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            options,
            text="GeoParquet",
            variable=self.geoparquet_var,
        ).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(
            options,
            text="Overwrite existing output",
            variable=self.overwrite_var,
        ).grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(
            options,
            text="Validate after conversion",
            variable=self.validate_var,
        ).grid(row=0, column=3, sticky="w")
        ttk.Checkbutton(
            options,
            text="GeoParquet large-output mode (bbox + grid sort)",
            variable=self.large_geoparquet_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(options, text="Chunk size").grid(row=1, column=2, sticky="e", pady=(8, 0))
        ttk.Entry(options, textvariable=self.chunk_size_var, width=12).grid(
            row=1, column=3, sticky="w", pady=(8, 0)
        )

        status_frame = ttk.Frame(root, padding=12)
        status_frame.grid(row=2, column=0, sticky="nsew")
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)

        self.status_text = tk.Text(status_frame, wrap="word", height=20, undo=False)
        self.status_text.grid(row=0, column=0, sticky="nsew")
        self.status_text.configure(insertwidth=0, takefocus=True)
        self.status_text.bind("<Button-1>", self._focus_status_text_event)
        self.status_text.bind("<<Cut>>", self._block_status_mutation_event)
        self.status_text.bind("<<Paste>>", self._block_status_mutation_event)
        self.status_text.bind("<BackSpace>", self._block_status_mutation_event)
        self.status_text.bind("<Delete>", self._block_status_mutation_event)
        self.status_text.bind("<Control-c>", self._copy_status_selection_event)
        self.status_text.bind("<Control-C>", self._copy_status_selection_event)
        self.status_text.bind("<Control-Key-c>", self._copy_status_selection_event)
        self.status_text.bind("<Control-Key-C>", self._copy_status_selection_event)
        self.status_text.bind("<Command-c>", self._copy_status_selection_event)
        self.status_text.bind("<Command-C>", self._copy_status_selection_event)
        self.status_text.bind("<Command-Key-c>", self._copy_status_selection_event)
        self.status_text.bind("<Command-Key-C>", self._copy_status_selection_event)
        root.bind_all("<<Copy>>", self._copy_status_if_relevant_event, add="+")
        root.bind_all("<Control-Key-c>", self._copy_status_if_relevant_event, add="+")
        root.bind_all("<Control-Key-C>", self._copy_status_if_relevant_event, add="+")
        root.bind_all("<Command-Key-c>", self._copy_status_if_relevant_event, add="+")
        root.bind_all("<Command-Key-C>", self._copy_status_if_relevant_event, add="+")
        self.status_text.bind("<Button-2>", self._show_status_context_menu)
        self.status_text.bind("<Button-3>", self._show_status_context_menu)
        self.status_text.bind("<Control-Button-1>", self._show_status_context_menu)
        self._status_context_menu = tk.Menu(self.status_text, tearoff=False)
        self._status_context_menu.add_command(
            label="Copy",
            command=self._copy_selected_status_text,
        )
        self._status_context_menu.add_command(
            label="Copy all",
            command=self._copy_all_status_text,
        )
        scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.status_text.configure(yscrollcommand=scrollbar.set)

        actions = ttk.Frame(root, padding=12)
        actions.grid(row=3, column=0, sticky="ew")
        actions.columnconfigure(4, weight=1)
        self.convert_button = ttk.Button(actions, text="Convert", command=self._start_conversion)
        self.convert_button.grid(row=0, column=0, padx=(0, 8))
        self.open_button = ttk.Button(
            actions,
            text="Open Output Directory",
            command=self._open_output_directory,
            state="disabled",
        )
        self.open_button.grid(row=0, column=1, padx=(0, 8))
        self.viewer_button = ttk.Button(
            actions,
            text="Show Viewer Instructions",
            command=self._show_viewer_instructions,
            state="disabled",
        )
        self.viewer_button.grid(row=0, column=2, padx=(0, 8))
        self.copy_button = ttk.Button(
            actions,
            text="Copy Text",
            command=self._copy_all_status_text,
        )
        self.copy_button.grid(row=0, column=3, padx=(0, 8))
        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=180)
        self.progress.grid(row=0, column=4, sticky="w")

        self._set_status(
            "Choose a local Darwin Core Archive file or unpacked directory, "
            "choose an output bundle directory, then convert."
        )

    def _choose_input(self) -> None:
        path = self.filedialog.askopenfilename(
            title="Choose DwC-A archive",
            filetypes=(("DwC-A zip archives", "*.zip"), ("All files", "*")),
        )
        if not path:
            path = self.filedialog.askdirectory(title="Choose unpacked DwC-A directory")
        if path:
            self.input_var.set(path)
            if not self.output_var.get().strip():
                source = Path(path)
                self.output_var.set(str(source.with_name(f"{source.stem}-bundle")))

    def _choose_output(self) -> None:
        path = self.filedialog.askdirectory(title="Choose output bundle directory")
        if path:
            self.output_var.set(path)

    def _request(self) -> GuiConversionRequest:
        formats = selected_output_formats(
            flatgeobuf=self.flatgeobuf_var.get(),
            geoparquet=self.geoparquet_var.get(),
        )
        return GuiConversionRequest(
            input_path=Path(self.input_var.get()).expanduser(),
            output_directory=Path(self.output_var.get()).expanduser(),
            output_formats=formats,
            overwrite=self.overwrite_var.get(),
            validate_after_conversion=self.validate_var.get(),
            geoparquet_large_output_mode=self.large_geoparquet_var.get(),
            chunk_size=parse_chunk_size(self.chunk_size_var.get()),
        )

    def _start_conversion(self) -> None:
        try:
            request = self._request()
            options = build_conversion_options(request)
        except ValueError as exc:
            self.messagebox.showerror("Cannot start conversion", str(exc))
            return

        self._last_result = None
        self.convert_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.viewer_button.configure(state="disabled")
        self.progress.start(10)
        self._set_status("Converting. Large bundles can take time while GDAL writes outputs.")

        thread = threading.Thread(
            target=self._run_conversion,
            args=(request, options),
            daemon=True,
        )
        thread.start()
        self.root.after(100, self._poll_queue)

    def _run_conversion(
        self,
        request: GuiConversionRequest,
        options: ConversionOptions,
    ) -> None:
        try:
            result = convert_dwca_archive(
                request.input_path,
                request.output_directory,
                options=options,
            )
            validation = (
                validate_output_bundle(result.output_directory)
                if request.validate_after_conversion
                else None
            )
        except ConversionError as exc:
            self._queue.put(("conversion_error", exc))
        except Exception as exc:  # pragma: no cover - defensive UI boundary.
            self._queue.put(("unexpected_error", exc))
        else:
            self._queue.put(("success", (result, validation)))

    def _poll_queue(self) -> None:
        try:
            kind, payload = self._queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_queue)
            return

        self.progress.stop()
        self.convert_button.configure(state="normal")
        if kind == "success":
            result, validation = payload
            self._last_result = result
            self.open_button.configure(state="normal")
            self.viewer_button.configure(state="normal")
            text = format_conversion_summary(result)
            if validation is not None:
                text = f"{text}\n\n{format_validation_summary(validation)}"
            text = f"{text}\n\n{viewer_instructions(result)}"
            self._set_status(text)
        elif kind == "conversion_error":
            exc = payload
            lines = [f"Conversion failed: {exc.message}"]
            for diagnostic in exc.diagnostics:
                if diagnostic.severity == "error":
                    lines.append(
                        f"- {diagnostic.source}: {diagnostic.code}: {diagnostic.message}"
                    )
            self._set_status("\n".join(lines))
            self.messagebox.showerror("Conversion failed", exc.message)
        else:
            self._set_status(f"Unexpected error: {payload}")
            self.messagebox.showerror("Unexpected error", str(payload))

    def _status_text_content(self) -> str:
        return self.status_text.get("1.0", "end-1c")

    def _selected_status_text(self) -> str:
        ranges = self.status_text.tag_ranges("sel")
        if not ranges:
            return ""
        return self.status_text.get(ranges[0], ranges[1])

    def _copy_text_to_clipboard(self, text: str) -> None:
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _copy_selected_status_text(self) -> None:
        self._copy_text_to_clipboard(self._selected_status_text())

    def _copy_all_status_text(self) -> None:
        self._copy_text_to_clipboard(self._status_text_content())

    def _copy_status_selection_event(self, event: Any) -> str:
        text = self._selected_status_text() or self._status_text_content()
        self._copy_text_to_clipboard(text)
        return "break"

    def _copy_status_if_relevant_event(self, event: Any) -> str | None:
        focus = self.root.focus_get()
        selected = self._selected_status_text()
        if focus == self.status_text or selected:
            self._copy_text_to_clipboard(selected or self._status_text_content())
            return "break"
        return None

    def _focus_status_text_event(self, event: Any) -> None:
        self.status_text.focus_set()

    def _block_status_mutation_event(self, event: Any) -> str:
        return "break"

    def _show_status_context_menu(self, event: Any) -> str:
        if self._status_context_menu is None:
            return "break"
        self.status_text.focus_set()
        try:
            self._status_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._status_context_menu.grab_release()
        return "break"

    def _set_status(self, text: str) -> None:
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", text)

    def _open_output_directory(self) -> None:
        if self._last_result is None:
            return
        open_path_in_file_manager(Path(self._last_result.output_directory))

    def _show_viewer_instructions(self) -> None:
        if self._last_result is None:
            return
        self._set_status(
            f"{format_conversion_summary(self._last_result)}\n\n"
            f"{viewer_instructions(self._last_result)}"
        )

    def run(self) -> int:
        self.root.mainloop()
        return 0


def open_path_in_file_manager(path: Path) -> None:
    """Open a path with the platform file manager."""

    system = platform.system()
    if system == "Windows":
        import os

        os.startfile(path)  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def run_gui() -> int:
    """Start the Tkinter GUI."""

    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError as exc:
        raise SystemExit(
            "Tkinter is not available in this Python environment. Install a Python "
            "build with Tk support or use the dwca-cloud-geospatial CLI."
        ) from exc

    try:
        app = _ConverterGui(tk, ttk, filedialog, messagebox)
    except tk.TclError as exc:
        raise SystemExit(
            "Tkinter could not open a desktop display. Run the GUI from a desktop "
            "session or use the dwca-cloud-geospatial CLI in headless environments."
        ) from exc
    return app.run()


def main() -> int:
    """Console-script entry point."""

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
