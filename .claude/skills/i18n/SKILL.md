---
name: i18n
description: Ekranik's translations (CLAUDE.md, rule 14) — write texts lupdate can find, update the .ts files, translate into Russian and Armenian with Windows' terms, build and check the .qm files. Use for any change that adds, changes or removes a visible text, and for translation work.
---

# Translations

English is the source language; Russian (`ru`) and Armenian (`hy`) are
translations. The change that adds or changes a text also translates it: the
tests fail on a text without a finished translation.

| File | What |
| --- | --- |
| `translations/ekranik_<ru,hy>.ts` | Translation sources, edited by hand or in Qt Linguist |
| `src/ekranik/translations/ekranik_<ru,hy>.qm` | Built from them, loaded by the app, committed |
| `tools/translations.py` | Runs lupdate and lrelease with the right options |
| `src/ekranik/i18n.py` | Picks the language and loads the `.qm` files |

## 1. Write texts lupdate can find

- In a widget: `self.tr("Text")`; anywhere else:
  `QCoreApplication.translate("Context", "Text")`. Set texts in the widget's
  `retranslate()`, which `changeEvent` calls on `QEvent.LanguageChange`.
- Literal strings only: lupdate reads the code, it doesn't run it, so
  `self.tr(variable)` and `self.tr(f"...")` are never translated. Insert values
  after translating: `self.tr("Saved to {folder}").format(folder=str(path))` —
  named fields, `str` values, and each translation keeps exactly the source's
  fields. With the first such text, teach `--check` to compare the fields: a
  broken one raises at `.format()` in that language only.
- lupdate files a text under the class the code is in. PySide6 looks it up
  under the object's class first, then under each base class (checked with a
  built `.qm`, PySide6 6.12), so a base class's `self.tr()` works in subclasses.
- "Ekranik" is a brand, never translated. Dialog buttons are Ekranik's own
  (`addButton`), since Qt resets standard buttons' texts.
- Plurals (`self.tr("%n recordings", "", n)`) also need English forms, and
  English loads no file today. With the first one: an `ekranik_en.ts` built
  with `-pluralonly`, English in the tool's `LANGUAGES` (its check then covers
  plural texts only), and `i18n.Translations.apply()` loading `ekranik_en.qm`.

## 2. Update and build

```powershell
uv run tools/translations.py
```

It runs lupdate (`-extensions py` before the folder, or lupdate finds nothing;
`-locations none -no-obsolete`, so the files change only with the texts), then
lrelease with `-nounfinished`, and lists the texts still untranslated. A new
text arrives as `<translation type="unfinished"></translation>`; a changed one
may arrive with lupdate's guess, also unfinished.

## 3. Translate

Fill each `<translation>` in both `.ts` files and delete `type="unfinished"`,
or use Qt Linguist (`uv run pyside6-linguist translations/ekranik_ru.ts`;
Ctrl+Enter marks a text done). Then run step 2 again: it builds the `.qm`
files and puts the `.ts` files back into lupdate's form.

Use Windows' established terms, never invented words (rule 14). The terms in
use, to keep them consistent:

| English | Русский | Հայերեն |
| --- | --- | --- |
| Settings | Параметры | Կարգավորումներ |
| OK · Cancel | ОК (Cyrillic) · Отмена | Լավ · Չեղարկել |
| Browse… | Обзор… | Զննել… |
| Restore default | По умолчанию | Վերականգնել լռելյայնը |
| Folder | Папка | Թղթապանակ |
| Microphone | Микрофон | Խոսափող |
| Screen recording (recording it) | Запись экрана | Էկրանի տեսագրում |
| A screen recording (the file) | Запись экрана | Էկրանի տեսագրություն |
| Audio recording (recording it) | Запись звука | Ձայնագրում |
| An audio recording (the file) | Аудиозапись | Ձայնագրություն |
| fps | кадров/с | կադր/վ |

Armenian sentences end with `։` (U+0589), not a period. Armenian names the act
of recording (`-ում`) and the recorded file (`-ություն`) differently, and has no
one word for both video and audio recordings: name the kind, or leave it out.

## 4. Check

```powershell
uv run tools/translations.py --check
```

It changes nothing and fails when a `.ts` file misses a text of the code, a
`.qm` file is not built from its `.ts` file, or a text has no finished
translation; `uv run pytest` runs it too (`tests/test_i18n.py`).

Then look at every changed screen in both languages for cut-off or wrapped
text. Never switch the user's own settings for that: render the window from a
script that first sends settings to a temporary folder (`QSettings.setPath`,
as `tests/conftest.py` does), sets `Settings.language` and saves
`widget.grab()` as a PNG.

Qt's own texts (key names, text-field menus) come from PySide6's
`qtbase_<lang>.qm`: Russian exists, Armenian does not (EKR-24).
