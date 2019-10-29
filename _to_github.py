# GitHub REST API

import __GH_API_TOKEN__
from github import Github
from github import InputGitTreeElement
import base64

g = Github(login_or_token=__GH_API_TOKEN__.token)
DA_ORG = g.get_organization(login="design-automation")
REPO = DA_ORG.get_repo("video-generator")
# REPO = g.get_user().get_repo("gitapi_test")

MASTER_REF = REPO.get_git_ref(ref="heads/master")
HEAD_COMMIT = REPO.get_git_commit(MASTER_REF.object.sha)
BASE_TREE = REPO.get_git_tree(MASTER_REF.object.sha)

def commit_n_push(paths, commit_msg):
    ele_list = []
    for path in paths:
        data = base64.b64encode(open(path, "rb").read())
        blob = REPO.create_git_blob(data.decode("utf-8"),"base64")
        element = InputGitTreeElement(path=path, mode="100644", type="blob", sha=blob.sha)
        ele_list.append(element)
    tree = REPO.create_git_tree(ele_list,BASE_TREE)
    commit = REPO.create_git_commit(message=commit_msg, tree=tree, parents=[HEAD_COMMIT])
    MASTER_REF.edit(commit.sha)
    print("\nNew Commit: %s" % commit.sha)
