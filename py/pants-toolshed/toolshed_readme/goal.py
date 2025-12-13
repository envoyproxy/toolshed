
import difflib
import pathlib
from typing import Dict, List, Optional, Tuple

from pants.engine.addresses import UnparsedAddressInputs
from pants.engine.console import Console
from pants.engine.goal import Goal, GoalSubsystem
from pants.engine.internals.selectors import MultiGet
from pants.option.option_types import StrOption
from pants.engine.rules import Get, collect_rules, goal_rule
from pants.engine.target import Targets
from pants.engine.unions import UnionMembership

import jinja2

from .snippet import (
    ReadmeSnippetFieldSet,
    ReadmeSnippetTemplateTagField,
    ReadmeSnippetTextField,
    ReadmeSnippet,
    ReadmeSnippetRequest,
    ReadmeSnippetTarget)


# returncode, stdout, stderr
ReadmeResultTuple = Tuple[int, Optional[str], Optional[str]]
ReadmeDataDict = Dict[str, List[ReadmeSnippet]]
ReadmeSnippetList = List[ReadmeSnippetTarget]
ReadmeSnippetTargetDict = Dict[str, ReadmeSnippetList]


class ReadmeSubsystem(GoalSubsystem):
    name = "readme"
    help = "Create a README file."

    check = StrOption(
        "--check",
        default="",
        help="...")
    fix = StrOption(
        "--fix",
        default="",
        help="...")


class Readme(Goal):
    subsystem_cls = ReadmeSubsystem
    environment_behavior = Goal.EnvironmentBehavior.LOCAL_ONLY


class ReadmeGoal:

    def __init__(
            self,
            targets: Targets,
            readme_subsystem: ReadmeSubsystem,
            union_membership: UnionMembership) -> None:
        self._targets = targets
        self.readme_subsystem = readme_subsystem
        self.union_membership = union_membership

    @property
    def action(self) -> Optional[str]:
        """Action, if set."""
        if self.readme_subsystem.options.check:
            return "check"
        if self.readme_subsystem.options.fix:
            return "fix"

    @property
    def action_file(self) -> Optional[pathlib.Path]:
        """File to work on with fix/check."""
        if self.readme_subsystem.options.check:
            return pathlib.Path(self.readme_subsystem.options.check)
        if self.readme_subsystem.options.fix:
            return pathlib.Path(self.readme_subsystem.options.fix)

    @property
    def target_types(self) -> Targets:
        """Applicable README snippet target types."""
        return ReadmeSnippetFieldSet.applicable_target_types(
            self._targets, self.union_membership)

    @property
    def targets(self) -> ReadmeSnippetTargetDict:
        """Targets separated into template_tags."""
        readme_targets: Dict = {}
        for target in self.target_types:
            template_tag = target[ReadmeSnippetTemplateTagField].value
            readme_targets[template_tag] = readme_targets.get(template_tag, [])
            readme_targets[template_tag].append(target)
        return readme_targets

    @property
    def template(self) -> jinja2.Template:
        return jinja2.Template(self.template_file.read_text())

    @property
    def template_file(self) -> pathlib.Path:
        # TODO: make this configurable/adaptable
        return pathlib.Path("templates/README.md.tmpl")

    def check_readme(self, data: str) -> Tuple[bool, Optional[str]]:
        file_content = self.action_file.read_text()
        if data != file_content:
            # TODO: improve diff
            return (
                False,
                "\n".join(
                    difflib.unified_diff(
                        data.split("\n"),
                        file_content.split("\n"))))
        return True, None

    def fix_readme(self, data: str) -> None:
        self.action_file.write_text(data)

    def get_requests(
            self,
            targets: ReadmeSnippetList,
            targets_set: Targets) -> List[ReadmeSnippetRequest]:
        """Get a list ReadmeSnippetRequests for these targets."""
        return [
            targets[i].readme_request_type(
                targets[i].readme_fieldset_type.create(targets[i]))
            for i, readme_target in enumerate(targets_set)]

    def handle(
            self,
            readme_data: ReadmeDataDict) -> ReadmeResultTuple:
        for k, v in readme_data.items():
            readme_data[k] = [sn.text.decode("utf-8") for sn in v]
        content = self.render(readme_data)
        if self.action == "check":
            return self.handle_check(content)
        elif self.action == "fix":
            return self.handle_fix(content)
        else:
            return 0, content, None

    def handle_check(self, content: str) -> ReadmeResultTuple:
        valid, diff = self.check_readme(content)
        if not valid:
            return (
                1,
                diff,
                (f"README ({self.action_file}) file did not match, "
                 f"run `pants readme --fix={self.action_file} ::` to fix"))
        return (
            0,
            f"README ({self.action_file}) is up-to-date",
            None)

    def handle_fix(self, content: str) -> ReadmeResultTuple:
        valid, diff = self.check_readme(content)
        if valid:
            return (
                1,
                None,
                f"README ({self.action_file}) is already correct")
        self.fix_readme(content)
        return (
            0,
            f"README ({self.action_file}) updated",
            None)

    def render(self, content_data: Dict[str, List[str]]) -> str:
        return self.template.render(**content_data)


@goal_rule
async def readme(
        console: Console,
        targets: Targets,
        readme_subsystem: ReadmeSubsystem,
        union_membership: UnionMembership) -> Readme:
    readme_rule = ReadmeGoal(targets, readme_subsystem, union_membership)
    readme_data: ReadmeDataDict = {}
    for template_tag, rule_targets in readme_rule.targets.items():
        readme_ruleset = await MultiGet(
            Get(Targets,
                UnparsedAddressInputs,
                (readme[ReadmeSnippetTextField]
                 .to_unparsed_address_inputs()))
            for readme in rule_targets)
        readme_data[template_tag] = await MultiGet(
            Get(ReadmeSnippet,
                ReadmeSnippetRequest,
                request)
            for request in readme_rule.get_requests(
                rule_targets,
                readme_ruleset))
    returncode, stdout, stderr = readme_rule.handle(readme_data)
    if stdout:
        console.print_stdout(stdout)
    if stderr:
        console.print_stderr(stderr)
    return Readme(exit_code=returncode)


def rules():
    return collect_rules()
