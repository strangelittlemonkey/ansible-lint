
# Copyright (c) 2020 Sorin Sbarnea <sorin.sbarnea@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import sys

from ansiblelint.rules import AnsibleLintRule


def _nested_search(term, data):
    return ((term in data) or
            reduce((lambda x, y: x or _nested_search(term, y)), _get_subtasks(data), False))


def _become_user_without_become(becomeuserabove, data):
    if 'become' in data:
        # If become is in lineage of tree then correct
        return False
    if ('become_user' in data and _nested_search('become', data)):
        # If 'become_user' on tree and become somewhere below
        # we must check for a case of a second 'become_user' without a
        # 'become' in its lineage
        subtasks = _get_subtasks(data)
        return reduce((lambda x, y: x or _become_user_without_become(False, y)), subtasks, False)
    if _nested_search('become_user', data):
        # Keep searching down if 'become_user' exists in the tree below current task
        subtasks = _get_subtasks(data)
        return (len(subtasks) == 0 or
                reduce((lambda x, y: x or
                        _become_user_without_become(
                            becomeuserabove or 'become_user' in data, y)), subtasks, False))
    # If at bottom of tree, flag up if 'become_user' existed in the lineage of the tree and
    # 'become' was not. This is an error if any lineage has a 'become_user' but no become
    return becomeuserabove


class RunOnceRule(AnsibleLintRule):
    """RunOnceRule Class."""

    id = "107"
    shortdesc = "Unpredictable run_once"
    description = (
        "Use of run_once does not work with free execution strategy. "
        "Avoid it, or use noqa comments to ignore it.")
    severity = 'MEDIUM'
    tags = ['unpredictability', 'experimental']
    version_added = 'v4.4.0'

    def matchtask(self, file, task):
        import pdb
        pdb.set_trace()
        return 'run_once' in task

    def matchplay(self, file, data):
        if file['type'] == 'playbook' and _become_user_without_become(False, data):
            return ({'become_user': data}, self.shortdesc)

EXAMPLE_PLAYBOOK = """
- name: play with free strategy
  hosts: localhost
  strategy: free
  tasks:

    - name: task that matches
      command: touch /tmp/foo
      run_once: true

    - name: task that does not match
      command: touch /tmp/foo
      run_once: true  # noqa 107

- name: play with serial strategy
  hosts: localhost
  strategy: serial
  tasks:

    - name: this task should not match rule
      command: touch /tmp/foo
      run_once: true

- name: play without strategy mentioned
  hosts: localhost
  strategy: serial
  tasks:

    - name: this task should match rule as strategy can change when used
      command: touch /tmp/foo
      run_once: true
"""


if "pytest" in sys.modules:

    import pytest

    @pytest.mark.parametrize('rule_runner', (RunOnceRule, ), indirect=['rule_runner'])
    def test_107(rule_runner):
        """Test rule matches."""
        results = rule_runner.run_playbook(EXAMPLE_PLAYBOOK)
        assert len(results) == 1
        assert isinstance(results[0].rule, RunOnceRule)
        assert results[0].linenumber == 6