"""Architecture diagram for saranreddy/aws-eventbridge-lambda-sqs-starter.

Verified against main @ 91a4606. Every node maps to infra/*.tf, src/lambda/handler.py
or scripts/*.py.

Render:  pip install diagrams   (also needs Graphviz: apt install graphviz / brew install graphviz)
         python docs/architecture.py   ->  docs/architecture.png (written next to this script)
"""
import os

from diagrams import Cluster, Diagram, Edge, getdiagram
from diagrams.aws.compute import LambdaFunction
from diagrams.aws.general import User
from diagrams.aws.integration import EventbridgeCustomEventBusResource, EventbridgeRule, SQS
from diagrams.aws.management import CloudwatchLogs
from diagrams.aws.security import IAMRole
from diagrams.onprem.iac import Terraform
from diagrams.programming.language import Python

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "architecture")  # -> architecture.png next to this script

FONT = "DejaVu Sans"
GRAPH = {
    "fontname": FONT, "fontsize": "34", "labelloc": "t", "pad": "0.4",
    "nodesep": "0.4", "ranksep": "1.0", "splines": "spline", "newrank": "true",
    "compound": "true",
}
NODE = {"fontname": FONT, "fontsize": "21", "imagepos": "tc"}
EDGE = {"fontname": FONT, "fontsize": "19", "color": "#555555",
        # enter/leave icons at mid-height so arrowheads never land on label text
        "tailport": "e", "headport": "w"}

# diagrams.Edge hard-codes a 13pt label font on every edge; raise it so edge labels stay
# readable when the PNG is scaled down to README width.
Edge._default_edge_attrs = {"fontcolor": "#2D3436", "fontname": FONT, "fontsize": "19"}


def box(bg, pen, style="rounded"):
    return {"bgcolor": bg, "pencolor": pen, "fontname": FONT, "fontsize": "21",
            "style": style, "labeljust": "l", "margin": "24"}


TF_BOX = box("#fff4e0", "#e66100")                  # deployed by Terraform
SUB_BOX = box("#fffaf2", "#e66100")                 # sub-group inside a Terraform box
RUN_BOX = box("#e8f1fb", "#1a5fb4")                 # created by scripts / CLI
EXEC_BOX = box("#f3eefa", "#613583")                # per execution / runtime
MANAGED_BOX = box("#f6f5f4", "#9a9996", "dashed")   # not created by this repo
ACCOUNT_BOX = box("#ffffff", "#232f3e")

FLOW = dict(color="#1a5fb4", fontcolor="#1a5fb4", penwidth="2.2")
IO = dict(color="#26a269", fontcolor="#1e7d4f", penwidth="1.8")
IAM = dict(color="#c01c28", fontcolor="#c01c28", style="dashed", penwidth="1.6", constraint="false")
AUX = dict(color="#8a8a8a", fontcolor="#5e5c64", style="dotted", penwidth="1.8")
SETUP = dict(color="#e66100", fontcolor="#c64600", style="dashed", penwidth="1.8")
MANUAL = dict(color="#26a269", fontcolor="#1e7d4f", style="dashed", penwidth="2.2")
FAIL = dict(color="#c01c28", fontcolor="#c01c28", penwidth="2.2")
OPT = dict(color="#b5835a", fontcolor="#8f5f3a", style="dashed", penwidth="1.8")
HIDDEN = dict(style="invis")
DOWN = dict(tailport="s", headport="n")
UP = dict(tailport="n", headport="s")


def same_rank(*nodes):
    getdiagram().dot.body.append("{rank=same; " + " ".join(f'"{n._id}";' for n in nodes) + "}")


GRAPH["nodesep"] = "0.8"
GRAPH["pad"] = "0.6"

with Diagram(
    "aws-eventbridge-lambda-sqs-starter",
    filename=OUT, outformat="png", show=False, direction="LR",
    graph_attr=GRAPH, node_attr=NODE, edge_attr=EDGE,
):
    eng = User("Engineer")
    tf = Terraform("terraform apply\n(infra/)")
    put = Python("put_event.py /\nsmoke_test.py")

    with Cluster("AWS account  (default us-east-1)", graph_attr=ACCOUNT_BOX):
        with Cluster("Deployed by Terraform", graph_attr=TF_BOX):
            bus = EventbridgeCustomEventBusResource("Custom\nevent bus\n<project>-bus")
            rule = EventbridgeRule("Rule\ndemo.exports /\nExportRequested")
            fn = LambdaFunction("Lambda processor\npython3.12\n2 async retries")
            queue = SQS("failed-events\nqueue")
            dlq = SQS("failed-events\nDLQ")
            logs = CloudwatchLogs("Log group\n/aws/lambda/\n<project>-processor\n7-day retention")
            role = IAMRole("Lambda\nexecution role")

    peek = Python("peek_queue.py")
    eng2 = User("Engineer\n(inspect)")

    eng >> Edge(label="deploy", **SETUP) >> tf
    tf >> Edge(**SETUP) >> bus
    eng >> Edge(label="run", **FLOW) >> put
    put >> Edge(label="PutEvents", weight="10", **FLOW) >> bus
    bus >> Edge(label="match", weight="10", **FLOW) >> rule
    rule >> Edge(label="async\ninvoke", weight="10", **FLOW) >> fn
    fn >> Edge(label="on failure\n(after retries)", weight="10", **FAIL) >> queue
    queue >> Edge(label="after 3\nreceives", weight="10", **FAIL) >> dlq
    fn >> Edge(label="logs", **AUX) >> logs
    bus >> Edge(**HIDDEN) >> role
    role >> Edge(label="assumed", **IAM) >> fn
    dlq >> Edge(**DOWN, **IO) >> peek
    queue >> Edge(label="peek / delete", tailport="s", headport="n", **IO) >> peek
    eng2 >> Edge(label="run", **MANUAL) >> peek
    same_rank(dlq, peek)
    same_rank(queue, eng2)
