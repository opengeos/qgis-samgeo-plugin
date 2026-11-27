"""Pure helper functions for the SamGeo plugin.

This module must not import ``qgis`` or any Qt binding, so its logic can be
unit tested without a running QGIS instance.
"""

import os
import re

# Model family keys used by the plugin.
FAMILY_SAM3 = "sam3"
FAMILY_SAM2 = "sam2"
FAMILY_SAM1 = "sam1"

# Weight choices for each model family as (label, value) pairs. The values
# are what the matching samgeo constructor accepts: ``SamGeo3(model_id=...)``,
# ``SamGeo2(model_id=...)`` and ``SamGeo(model_type=...)``. The first entry of
# each list is the default and matches samgeo's own default.
MODEL_WEIGHTS = {
    FAMILY_SAM3: [
        ("SAM 3", "facebook/sam3"),
        ("SAM 3.1 (meta backend only)", "facebook/sam3.1"),
    ],
    FAMILY_SAM2: [
        ("Large (hiera-large)", "sam2-hiera-large"),
        ("Base+ (hiera-base-plus)", "sam2-hiera-base-plus"),
        ("Small (hiera-small)", "sam2-hiera-small"),
        ("Tiny (hiera-tiny)", "sam2-hiera-tiny"),
    ],
    FAMILY_SAM1: [
        ("ViT-H (huge)", "vit_h"),
        ("ViT-L (large)", "vit_l"),
        ("ViT-B (base)", "vit_b"),
    ],
}

# Attribute fields added to saved vector masks.
SOURCE_FIELD = "source"
PROMPT_FIELD = "prompt"

# Prompt types recorded in the ``prompt`` field.
PROMPT_TEXT = "text"
PROMPT_POINT = "point"
PROMPT_BOX = "box"
PROMPT_BATCH_POINT = "batch_point"

# Output file extensions keyed by a keyword of the Output tab format combo.
_FORMAT_EXTENSIONS = (
    ("GeoPackage", ".gpkg"),
    ("Shapefile", ".shp"),
    ("Raster", ".tif"),
)


def model_family(label):
    """Return the model family key for a model combo label.

    Args:
        label: Text of the model combo, e.g. ``"SamGeo2 (SAM2)"``.

    Returns:
        One of ``"sam3"``, ``"sam2"`` or ``"sam1"``. Unknown labels map to
        ``"sam1"``, matching the plugin's historical fallback to ``SamGeo``.
    """
    if "SamGeo3" in label:
        return FAMILY_SAM3
    if "SamGeo2" in label:
        return FAMILY_SAM2
    return FAMILY_SAM1


def model_weight_options(family):
    """Return the weight choices for a model family.

    Args:
        family: A model family key such as ``"sam2"``.

    Returns:
        A list of ``(label, value)`` tuples, default first. Unknown families
        return an empty list.
    """
    return list(MODEL_WEIGHTS.get(family, []))


def default_model_weight(family):
    """Return the default weight value for a model family.

    Args:
        family: A model family key such as ``"sam1"``.

    Returns:
        The default value (e.g. ``"vit_h"``), or None for unknown families.
    """
    options = MODEL_WEIGHTS.get(family)
    return options[0][1] if options else None


def model_constructor_kwargs(family, weight):
    """Build the weight keyword argument for a samgeo model constructor.

    Args:
        family: A model family key such as ``"sam2"``.
        weight: The selected weight value, or None/empty for the default.

    Returns:
        A dict to splat into the constructor: ``{"model_id": ...}`` for SAM3
        and SAM2, ``{"model_type": ...}`` for SAM1.

    Raises:
        ValueError: If ``weight`` is not a valid choice for ``family``.
    """
    if not weight:
        weight = default_model_weight(family)
    valid = [value for _, value in MODEL_WEIGHTS.get(family, [])]
    if weight not in valid:
        raise ValueError(
            f"Invalid model weights {weight!r} for {family}. "
            f"Choose one of: {', '.join(valid)}"
        )
    key = "model_type" if family == FAMILY_SAM1 else "model_id"
    return {key: weight}


def source_name(source_path):
    """Return the file name of a source raster for the ``source`` field.

    QGIS layer sources may carry provider options after a ``|`` (for example
    ``image.tif|layername=x``); those are dropped. Both ``/`` and ``\\`` are
    treated as separators so Windows paths work on any platform.

    Args:
        source_path: Path or QGIS layer source of the raster, or None.

    Returns:
        The file name, e.g. ``"my image.tif"``, or an empty string.
    """
    if not source_path:
        return ""
    path = str(source_path).split("|", 1)[0].strip()
    path = path.rstrip("/\\")
    return re.split(r"[/\\]", path)[-1]


def mask_attributes(source_path, prompt_type):
    """Return the attribute values written to every saved vector mask.

    Args:
        source_path: Path of the segmented source raster.
        prompt_type: Prompt type, e.g. ``"text"``, ``"point"`` or ``"box"``.

    Returns:
        A dict mapping field name to value, e.g.
        ``{"source": "image.tif", "prompt": "text"}``.
    """
    return {
        SOURCE_FIELD: source_name(source_path),
        PROMPT_FIELD: prompt_type or "",
    }


def output_extension(format_text):
    """Return the file extension for an Output tab format label.

    Args:
        format_text: Text of the output format combo, e.g.
            ``"Vector (GeoPackage)"``.

    Returns:
        ``".gpkg"``, ``".shp"`` or ``".tif"`` (the default).
    """
    for keyword, extension in _FORMAT_EXTENSIONS:
        if keyword in format_text:
            return extension
    return ".tif"


def source_directory(source_path):
    """Return the directory of a source raster if it exists.

    Args:
        source_path: Path or QGIS layer source of the raster, or None.

    Returns:
        The absolute directory path, or an empty string when the source is
        unset or its directory does not exist.
    """
    if not source_path:
        return ""
    path = str(source_path).split("|", 1)[0].strip()
    directory = os.path.dirname(os.path.abspath(path))
    return directory if os.path.isdir(directory) else ""


def _safe_token(text):
    """Make a short, file-name-safe token from free text.

    Args:
        text: Arbitrary text such as a prompt type.

    Returns:
        The text with runs of unsafe characters replaced by ``_``.
    """
    return re.sub(r"[^\w.-]+", "_", str(text)).strip("_")


def default_output_path(source_path, prompt_type, extension, ensure_unique=True):
    """Suggest an output path next to the source raster.

    The name is ``<source stem>_<prompt>_masks<extension>``; with
    ``ensure_unique`` a numeric suffix is added so an existing file is never
    overwritten.

    Args:
        source_path: Path of the segmented source raster.
        prompt_type: Prompt type used for the masks, or None.
        extension: Output extension including the dot, e.g. ``".gpkg"``.
        ensure_unique: Append ``_1``, ``_2``, ... if the path already exists.

    Returns:
        The suggested path, or an empty string when the source directory is
        unknown.
    """
    directory = source_directory(source_path)
    if not directory:
        return ""
    stem = os.path.splitext(source_name(source_path))[0] or "samgeo"
    parts = [stem]
    token = _safe_token(prompt_type) if prompt_type else ""
    if token:
        parts.append(token)
    parts.append("masks")
    base = os.path.join(directory, "_".join(parts))
    candidate = base + extension
    if ensure_unique:
        index = 1
        while os.path.exists(candidate):
            candidate = f"{base}_{index}{extension}"
            index += 1
    return candidate
