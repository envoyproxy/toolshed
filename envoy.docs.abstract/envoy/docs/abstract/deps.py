
import abc
import pathlib
import urllib.parse
from collections import defaultdict, namedtuple
from typing import Any, Dict

import abstracts

from .builder import ADocsBuilder
from .formatter import ARSTFormatter


RepositoryLocationsDict = Dict[str, Any]

CSV_TABLE_TEMPLATE = """.. csv-table::
  :header: {headers}
  :widths: {widths}

  {csv_rows}

"""

NIST_CPE_URL_TEMPLATE = (
    "https://nvd.nist.gov/vuln/search/results?form_type=Advanced&"
    "results_type=overview&query={encoded_cpe}&search_type=all")


# Obtain GitHub project URL from a list of URLs.
def get_github_project_url(urls):
    for url in urls:
        if not url.startswith('https://github.com/'):
            continue
        components = url.split('/')
        return f'https://github.com/{components[3]}/{components[4]}'
    return None


# Information releated to a GitHub release version.
GitHubRelease = namedtuple(
    'GitHubRelease',
    ['organization', 'project', 'version', 'tagged'])


# Search through a list of URLs and determine if any contain a GitHub URL. If
# so, use heuristics to extract the release version and repo details, return
# this, otherwise return None.
def get_github_release_from_urls(urls):
    for url in urls:
        if not url.startswith('https://github.com/'):
            continue
        components = url.split('/')
        if components[5] == 'archive':
            # Only support .tar.gz, .zip today. Figure out the release tag from
            # this filename.
            if components[6].endswith('.tar.gz'):
                github_version = components[6][:-len('.tar.gz')]
            else:
                assert (components[6].endswith('.zip'))
                github_version = components[6][:-len('.zip')]
        else:
            # Release tag is a path component.
            assert (components[5] == 'releases')
            github_version = components[7]
        # If it's not a GH hash, it's a tagged release.
        tagged_release = len(github_version) != 40
        return GitHubRelease(
            organization=components[3],
            project=components[4],
            version=github_version,
            tagged=tagged_release)
    return None


class ADependenciesDocsBuilder(ADocsBuilder, metaclass=abstracts.Abstraction):

    @property
    def csv_table_template(self):
        return CSV_TABLE_TEMPLATE

    @property
    def extension_dependencies(self):
        # Generate per-use category RST with CSV tables.
        for category, exts in self.use_categories.items():
            content = ''
            output_path = self.security_rst_root.joinpath(
                f'external_dep_{category}.rst')
            for ext_name, deps in sorted(exts.items()):
                if ext_name != 'core':
                    content += self.rst_formatter.header(ext_name)
                content += self.csv_table(
                    ['Name', 'Version', 'Release date', 'CPE'], [2, 1, 1, 2],
                    [[dep.name, dep.version, dep.release_date, dep.cpe]
                     for dep
                     in sorted(deps, key=lambda d: d.sort_name)])
            yield output_path, content

    @property
    def nist_cpe_url_template(self):
        return NIST_CPE_URL_TEMPLATE

    @property
    @abc.abstractmethod
    def repository_locations(self) -> RepositoryLocationsDict:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def rst_formatter(self) -> ARSTFormatter:
        raise NotImplementedError

    @property
    def security_rst_root(self) -> pathlib.PurePosixPath:
        return pathlib.PurePosixPath("intro/arch_overview/security")

    @property
    def use_categories(self):
        Dep = namedtuple(
            'Dep',
            ['name', 'sort_name', 'version', 'cpe', 'release_date'])
        use_categories = defaultdict(lambda: defaultdict(list))
        # Bin rendered dependencies into per-use category lists.
        for k, v in self.repository_locations.items():
            cpe = v.get('cpe', '')
            if cpe == 'N/A':
                cpe = ''
            if cpe:
                cpe = self.rst_formatter.external_link(
                    cpe, self.nist_cpe_url(cpe))
            project_name = v['project_name']
            project_url = v['project_url']
            name = self.rst_formatter.external_link(project_name, project_url)
            version = self.rst_formatter.external_link(
                self.rst_formatter.version(v['version']),
                self.get_version_url(v))
            release_date = v['release_date']
            dep = Dep(name, project_name.lower(), version, cpe, release_date)
            for category in v['use_category']:
                for ext in v.get('extensions', ['core']):
                    use_categories[category][ext].append(dep)
        return use_categories

    async def build(self):
        for output_path, content in self.extension_dependencies:
            self.out(output_path, content)

    # Render a CSV table given a list of table headers, widths and list of rows
    # (each a list of strings).
    def csv_table(self, headers, widths, rows):
        return self.csv_table_template.format(
            headers=', '.join(headers),
            csv_rows='\n  '.join(', '.join(row) for row in rows),
            widths=', '.join(str(w) for w in widths))

    # Determine the version link URL. If it's GitHub, use some heuristics to
    # figure out a release tag link, otherwise point to the GitHub tree at the
    # respective SHA. Otherwise, return the tarball download.
    def get_version_url(self, metadata):
        # Figure out if it's a GitHub repo.
        github_release = get_github_release_from_urls(metadata['urls'])
        # If not, direct download link for tarball
        if not github_release:
            return metadata['urls'][0]
        github_repo = (
            "https://github.com/"
            f"{github_release.organization}/{github_release.project}")
        if github_release.tagged:
            # The GitHub version should look like the metadata version,
            # but might have something like a "v" prefix.
            return f'{github_repo}/releases/tag/{github_release.version}'
        assert (metadata['version'] == github_release.version)
        return f'{github_repo}/tree/{github_release.version}'

    # NIST CPE database search URL for a given CPE.
    def nist_cpe_url(self, cpe):
        return self.nist_cpe_url_template.format(
            encoded_cpe=urllib.parse.quote(cpe))
