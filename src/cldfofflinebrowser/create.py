"""
Data access functionality required for the offline browser.
"""
import decimal
import logging
import functools
import itertools
import mimetypes
import collections
import pathlib
from collections.abc import Generator, Iterator
import dataclasses
from typing import Optional, Any

from csvw.metadata import Table
from csvw.datatypes import anyURI
import pycldf

from . import media

# Forms grouped by language and parameter.
GroupedFormsType = tuple[str, dict[str, list[collections.OrderedDict[str, Any]]]]


@dataclasses.dataclass
class Data:  # pylint: disable=R0902
    """Convenient access to data from a CLDF dataset."""
    title: str
    title_tooltip: str
    languages: dict[str, dict[str, Any]]
    parameters: dict[str, dict[str, Any]]
    forms: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)
    audio: dict = dataclasses.field(default_factory=dict)
    form2audio: dict[str, str] = dataclasses.field(default_factory=dict)
    media_table: Optional[Table] = None

    @classmethod
    def from_dataset(
            cls,
            cldf: pycldf.Dataset,
            include_parameters: Optional[list[str]] = None,
            with_audio: bool = False,
            log: Optional[logging.Logger] = None,
    ):
        """Initialize a data object from the data in a CLDF dataset."""
        def _augmented_dict(lang):
            lang['has_audio'] = False
            return {
                k: float(v) if isinstance(v, decimal.Decimal) else v
                for k, v in lang.items()
                if k not in ('Latitude', 'Longitude')}

        title_ = cldf.properties['dc:title'].replace('"', '”')

        res = cls(
            title=f'<div class="truncate">{title_}.</div>',
            title_tooltip=title_,
            languages={
                lang['id']: _augmented_dict(lang)
                for lang in cldf.iter_rows('LanguageTable', 'latitude', 'longitude', 'id', 'name')
                if lang['latitude'] is not None and lang['longitude'] is not None},
            parameters={
                param['id']: {
                    'id': param['id'],
                    'name': param['name'],
                    'representation': set(),
                    'has_audio': False,
                }
                for param in cldf.iter_rows('ParameterTable', 'id', 'name')
                if include_parameters is None or param['id'] in include_parameters},
        )
        for form in cldf.iter_rows(
                'FormTable', 'id', 'languageReference', 'parameterReference', 'form'):
            if form['languageReference'] in res.languages \
                    and form['parameterReference'] in res.parameters:
                res.forms[form['id']] = form
        if with_audio:
            res._load_audio(cldf, log)

        # tell parameter table about languages with values
        for form in res.forms.values():
            pid = form['parameterReference']
            res.parameters[pid]['representation'].add(form['languageReference'])

        # tell language and parameter table about audio files
        for fid in res.form2audio:
            res.languages[res.forms[fid]['languageReference']]['has_audio'] = True
            res.parameters[res.forms[fid]['parameterReference']]['has_audio'] = True

        return res

    @functools.cached_property
    def template_context(self) -> dict[str, Any]:
        """
        The template context necessary to create navigation and header.
        """
        def get_name(item):
            return item[1]['name'].lower()

        return {
            'parameters': sorted(self.parameters.items(), key=get_name),
            'languages': sorted(self.languages.items(), key=get_name),
            'title_tooltip': self.title_tooltip,
            'title': self.title,
        }

    def _iter_forms_by(
            self,
            ref: str,
            secondary: str,
    ) -> Generator[tuple[str, Iterator[dict[str, Any]]], None, None]:
        yield from itertools.groupby(
            sorted(self.forms.values(), key=lambda r: (r[ref], r[secondary], r['id'])),
            lambda r: r[ref])

    def iter_forms_by_language(self) -> Generator[GroupedFormsType, None, None]:
        """Yield lists of forms grouped into languages and then parameters."""
        secondary = 'parameterReference'
        for lid, forms in self._iter_forms_by('languageReference', secondary):
            yield lid, {pid: list(fs) for pid, fs in
                        itertools.groupby(forms, lambda r: r[secondary])}

    def iter_forms_by_parameter(self) -> Generator[GroupedFormsType, None, None]:
        """Yield lists of forms grouped into parameters and then languages."""
        secondary = 'languageReference'
        for pid, forms in self._iter_forms_by('parameterReference', secondary):
            yield pid, {lid: list(fs) for lid, fs in
                        itertools.groupby(forms, lambda r: r[secondary])}

    def _forms_for_page_data(self, forms):
        return [
            {
                'form': form['form'],
                'audio': {
                    'name': f"../parameter-{form['parameterReference']}/"
                            f"{self.audio[self.form2audio[form['id']]]['file-path'].name}",
                    'mediaType': self.audio[self.form2audio[form['id']]]['mediaType'],
                } if form['id'] in self.form2audio else None,
            } for form in forms]

    def parameter_page_data(self, forms):
        """JSON serializable data for a parameter page."""
        pforms = {lid: self._forms_for_page_data(fs) for lid, fs in forms.items()}
        return {'languages': {lid: self.languages[lid] for lid in pforms}, 'forms': pforms}

    def language_page_data(self, forms):
        """JSON serializable data for a language page."""
        lang_forms = {pid: self._forms_for_page_data(fs) for pid, fs in forms.items()}
        lang_parameters = {
            pid: {'id': self.parameters[pid]['name'], 'name': self.parameters[pid]['name']}
            for pid in lang_forms}
        return {'parameters': lang_parameters, 'forms': lang_forms}

    def iter_missing_audio(
            self,
            cldf: pycldf.Dataset,
            outdir: pathlib.Path,
    ) -> Generator[tuple[pathlib.Path, str], None, None]:
        """Yield pairs specifying audio files not yet part of the offline browser."""
        for fid, aid in self.form2audio.items():
            pid = self.forms[fid]['parameterReference']
            audio_file = self.audio[aid]
            suffix = media.PREFERRED_AUDIO.get(audio_file['mediaType']) \
                or mimetypes.guess_extension(audio_file['mediaType']) \
                or '.bin'
            p = audio_file['file-path'] = outdir / f'parameter-{pid}' / f'{fid}{suffix}'
            if not p.exists():
                yield p, anyURI.to_string(cldf.get_row_url(self.media_table, audio_file))

    def _load_audio(self, cldf, log):
        # We check for the MediaTable component first, and then fall back to
        # a list of audio files in a table "media.csv", with a column
        # "mimetype".
        self.media_table = cldf.get('MediaTable') or cldf.get('media.csv')
        if self.media_table is None:  # pragma: no cover
            log.error('No media table found')
            return

        id_col = self.media_table.get_column('http://cldf.clld.org/v1.0/terms.rdf#id')
        id_col = id_col.name if id_col is not None else 'ID'
        mtype_col = self.media_table.get_column('http://cldf.clld.org/v1.0/terms.rdf#mediaType')
        mtype_col = mtype_col.name if mtype_col is not None else 'mimetype'

        audio = {
            row[id_col]: row
            for row in self.media_table
            if row.get(id_col) and row[mtype_col].startswith('audio/')}
        # normalise relevant column headers to their CLDF property names to reduce headache
        media_colmap = {id_col: 'id', mtype_col: 'mediaType'}
        self.audio = {
            aid: {media_colmap.get(k, k): v for k, v in audio_file.items()}
            for aid, audio_file in audio.items()}

        # look for form references in the media table
        form2audio = collections.defaultdict(list)
        form_id_field = (
            self.media_table.get_column('http://cldf.clld.org/v1.0/terms.rdf#formReference')
            or self.media_table.get_column('Form_ID'))
        if form_id_field:
            for audio_file in self.audio.values():
                fid = audio_file.get(form_id_field.name)
                if not fid:
                    continue
                if not isinstance(fid, list):
                    fid = [fid]
                for single_fid in fid:
                    form2audio[single_fid].append(audio_file['id'])

        # look for media references in the form table
        audio_id_field = (
            cldf.get(('FormTable', 'mediaReference')) or cldf.get(('FormTable', 'Audio_Files')))
        if audio_id_field:
            for form in self.forms.values():
                audio_ids = form.get(audio_id_field.name)
                if not audio_ids:
                    continue
                if isinstance(audio_ids, list):
                    form2audio[form['id']].extend(audio_ids)
                else:
                    form2audio[form['id']].append(audio_ids)

        form2audio = {
            fid: media.get_best_audio([self.audio[mid] for mid in mids if mid in self.audio])
            for fid, mids in form2audio.items()}
        self.form2audio = {
            fid: audio_file['id']
            for fid, audio_file in form2audio.items()
            if audio_file is not None and fid in self.forms}
