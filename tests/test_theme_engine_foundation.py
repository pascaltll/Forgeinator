import json
import tempfile
import unittest
from pathlib import Path

from hub.themes import ThemeEngine, migrate_v285, resolve, save_config, load_config
from hub.themes.schema import ThemeValidationError
from hub.themes.registry import PRESETS, PALETTES, LAYOUTS, MATERIALS


class RegistryTests(unittest.TestCase):
    def test_eight_presets_registered(self):
        self.assertEqual(set(PRESETS), {"minimal", "showcase", "glass", "flow", "arcade", "terminal", "editorial", "brutalist"})

    def test_every_preset_default_references_registered_components(self):
        for preset in PRESETS.values():
            self.assertIn(preset.default_layout, LAYOUTS)
            self.assertIn(preset.default_palette, PALETTES)
            self.assertIn(preset.default_material, MATERIALS)
            for layout in preset.supported_layouts:
                self.assertIn(layout, LAYOUTS)
            for palette in preset.supported_palettes:
                self.assertIn(palette, PALETTES)


class ResolverTests(unittest.TestCase):
    def test_default_resolves(self):
        a = resolve({})
        self.assertEqual(a.preset, "minimal")
        self.assertEqual(a.layout, "posters")
        self.assertEqual(a.palette, "obsidian")

    def test_invalid_ids_fall_back_to_preset_defaults(self):
        a = resolve({"active_preset": "not-a-theme", "appearance": {"layout": "nope", "palette": {"id": "nope"}, "material": "nope"}})
        self.assertEqual(a.preset, "minimal")
        self.assertEqual(a.layout, "posters")
        self.assertEqual(a.palette, "obsidian")
        self.assertEqual(a.material, "solid")

    def test_palette_does_not_change_layout_or_audio(self):
        engine = ThemeEngine()
        before = engine.appearance
        after = engine.update(palette="ocean")
        self.assertEqual(after.layout, before.layout)
        self.assertEqual(after.audio, before.audio)

    def test_user_overrides_win(self):
        a = resolve({"active_preset": "glass", "appearance": {"layout": "grid", "palette": {"id": "violet"}, "geometry": {"radius": 20}}})
        self.assertEqual(a.layout, "grid")
        self.assertEqual(a.palette, "violet")
        self.assertEqual(a.geometry["radius"], 20)

    def test_rgb_out_of_range_rejected(self):
        with self.assertRaises(ThemeValidationError):
            resolve({"appearance": {"colors": {"BG": [0, 0, 999]}}})

    def test_untrusted_numeric_values_are_clamped(self):
        a = resolve({"appearance": {"geometry": {"radius": 999}, "motion": {"speed": -20}, "audio": {"volume": 4}}})
        self.assertEqual(a.geometry["radius"], 32)
        self.assertEqual(a.motion["speed"], 0.1)
        self.assertEqual(a.audio["volume"], 1.0)


class MigrationTests(unittest.TestCase):
    def test_all_known_legacy_themes_map(self):
        legacy = ["dark", "light", "limpio", "quiver", "prototipo", "cristal", "aurora", "onda", "tarjeta", "cubo", "interruptor", "brasa", "pixel", "retro16", "neon", "fosforo", "tinta", "bloque"]
        for theme in legacy:
            with self.subTest(theme=theme):
                migrated = migrate_v285({"theme": theme})
                self.assertIn(migrated["active_preset"], PRESETS)
                self.assertIn(migrated["appearance"]["layout"], LAYOUTS)

    def test_migration_does_not_mutate_input(self):
        old = {"theme": "pixel", "pals": {"pixel": "16bits"}, "bgs": {"pixel": "stars"}, "fx": "perf"}
        original = json.loads(json.dumps(old))
        migrate_v285(old)
        self.assertEqual(old, original)

    def test_perf_fx_maps_to_low_blur(self):
        a = migrate_v285({"theme": "cristal", "fx": "perf"})["appearance"]["render"]
        self.assertEqual(a, {"quality": "low", "blur_enabled": False})


class PersistenceTests(unittest.TestCase):
    def test_atomic_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "appearance.json"
            config = {"schema_version": 1, "active_preset": "glass", "appearance": {"layout": "mosaic"}}
            save_config(path, config)
            self.assertEqual(load_config(path), config)

    def test_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_config(Path(tmp) / "missing.json")["active_preset"], "minimal")


if __name__ == "__main__":
    unittest.main()
