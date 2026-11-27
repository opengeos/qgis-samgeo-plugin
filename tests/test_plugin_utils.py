"""Unit tests for the QGIS-free helpers in ``plugin_utils``."""

import os

import pytest

from samgeo_plugin import plugin_utils as pu


@pytest.mark.parametrize(
    "label, family",
    [
        ("SamGeo3 (SAM3)", "sam3"),
        ("SamGeo2 (SAM2)", "sam2"),
        ("SamGeo (SAM1)", "sam1"),
        ("something else", "sam1"),
    ],
)
def test_model_family(label, family):
    assert pu.model_family(label) == family


def test_weight_options_match_samgeo_values():
    sam1 = [value for _, value in pu.model_weight_options("sam1")]
    sam2 = [value for _, value in pu.model_weight_options("sam2")]
    sam3 = [value for _, value in pu.model_weight_options("sam3")]
    assert sorted(sam1) == ["vit_b", "vit_h", "vit_l"]
    assert sorted(sam2) == [
        "sam2-hiera-base-plus",
        "sam2-hiera-large",
        "sam2-hiera-small",
        "sam2-hiera-tiny",
    ]
    assert sam3 == ["facebook/sam3", "facebook/sam3.1"]
    assert pu.model_weight_options("nope") == []


def test_defaults_keep_samgeo_defaults():
    assert pu.default_model_weight("sam1") == "vit_h"
    assert pu.default_model_weight("sam2") == "sam2-hiera-large"
    assert pu.default_model_weight("sam3") == "facebook/sam3"
    assert pu.default_model_weight("nope") is None


def test_model_constructor_kwargs():
    assert pu.model_constructor_kwargs("sam1", "vit_b") == {"model_type": "vit_b"}
    assert pu.model_constructor_kwargs("sam2", "sam2-hiera-tiny") == {
        "model_id": "sam2-hiera-tiny"
    }
    assert pu.model_constructor_kwargs("sam3", None) == {"model_id": "facebook/sam3"}
    assert pu.model_constructor_kwargs("sam1", "") == {"model_type": "vit_h"}
    with pytest.raises(ValueError):
        pu.model_constructor_kwargs("sam1", "sam2-hiera-tiny")


@pytest.mark.parametrize(
    "source, expected",
    [
        ("/data/images/scene.tif", "scene.tif"),
        (r"C:\Users\me\My Images\scene 1.tif", "scene 1.tif"),
        ("C:/mixed\\path/scene.tif", "scene.tif"),
        ("/data/image.gpkg|layername=rgb", "image.gpkg"),
        ("scene.tif", "scene.tif"),
        ("", ""),
        (None, ""),
    ],
)
def test_source_name(source, expected):
    assert pu.source_name(source) == expected


def test_mask_attributes():
    assert pu.mask_attributes("/x/My Scene.tif", "box") == {
        "source": "My Scene.tif",
        "prompt": "box",
    }
    assert pu.mask_attributes(None, None) == {"source": "", "prompt": ""}


@pytest.mark.parametrize(
    "text, ext",
    [
        ("Raster (GeoTIFF)", ".tif"),
        ("Vector (GeoPackage)", ".gpkg"),
        ("Vector (Shapefile)", ".shp"),
        ("unknown", ".tif"),
    ],
)
def test_output_extension(text, ext):
    assert pu.output_extension(text) == ext


def test_source_directory(tmp_path):
    image = tmp_path / "dir with space" / "scene.tif"
    image.parent.mkdir()
    image.write_bytes(b"")
    assert pu.source_directory(str(image)) == str(image.parent)
    assert pu.source_directory(str(tmp_path / "missing" / "scene.tif")) == ""
    assert pu.source_directory("") == ""
    assert pu.source_directory(None) == ""


def test_default_output_path_next_to_source(tmp_path):
    folder = tmp_path / "my images"
    folder.mkdir()
    image = folder / "wa building.tif"
    image.write_bytes(b"")

    path = pu.default_output_path(str(image), "text", ".gpkg")
    assert path == os.path.join(str(folder), "wa building_text_masks.gpkg")

    # Existing outputs are never overwritten.
    open(path, "w").close()
    second = pu.default_output_path(str(image), "text", ".gpkg")
    assert second == os.path.join(str(folder), "wa building_text_masks_1.gpkg")
    open(second, "w").close()
    assert pu.default_output_path(str(image), "text", ".gpkg").endswith("_masks_2.gpkg")
    assert pu.default_output_path(str(image), "text", ".gpkg", ensure_unique=False) == (
        path
    )


def test_default_output_path_without_prompt_or_source(tmp_path):
    image = tmp_path / "scene.tif"
    image.write_bytes(b"")
    assert pu.default_output_path(str(image), None, ".shp") == os.path.join(
        str(tmp_path), "scene_masks.shp"
    )
    assert pu.default_output_path(str(image), "a/b c", ".tif") == os.path.join(
        str(tmp_path), "scene_a_b_c_masks.tif"
    )
    assert pu.default_output_path(None, "text", ".tif") == ""
