"""Deploy the demo UI to ECS Fargate behind a public Application Load Balancer.

Reads GEMINI_API_KEY from local .env (never prints it) and injects it as a
task environment variable so reviewers can run live investigations.

    python scripts/deploy_ecs.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import dotenv_values


REGION = "us-east-1"
NAME = "idea-diligence-agent"
CLUSTER = NAME
CONTAINER_PORT = 8000
REPO_ROOT = Path(__file__).resolve().parents[1]


def _log(message: str) -> None:
    print(message, flush=True)


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, cwd=str(REPO_ROOT), **kwargs)


def gemini_key() -> str:
    values = dotenv_values(REPO_ROOT / ".env")
    key = (values.get("GEMINI_API_KEY") or "").strip()
    if not key or key.startswith("your_"):
        raise SystemExit("GEMINI_API_KEY is missing from .env; live reviews would fail.")
    return key


def ensure_ecr(ecr) -> str:
    try:
        ecr.create_repository(repositoryName=NAME, imageTagMutability="MUTABLE")
        _log(f"Created ECR repository {NAME}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "RepositoryAlreadyExistsException":
            raise
    uri = ecr.describe_repositories(repositoryNames=[NAME])["repositories"][0]["repositoryUri"]
    return uri


def push_image(ecr, uri: str) -> str:
    account, _, _ = uri.partition(".")
    password = subprocess.check_output(
        ["aws", "ecr", "get-login-password", "--region", REGION],
        text=True,
    ).strip()
    login = subprocess.run(
        ["docker", "login", "--username", "AWS", "--password-stdin", f"{account}.dkr.ecr.{REGION}.amazonaws.com"],
        input=password,
        text=True,
        check=True,
        cwd=str(REPO_ROOT),
    )
    del password, login
    image = f"{uri}:latest"
    _log("Building and pushing linux/amd64 image (this takes a few minutes)...")
    _run(["docker", "buildx", "build", "--platform", "linux/amd64", "-t", image, "--push", "."])
    return image


def ensure_logs(logs) -> None:
    try:
        logs.create_log_group(logGroupName=f"/ecs/{NAME}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceAlreadyExistsException":
            raise


def default_network(ec2) -> tuple[str, list[str]]:
    vpc = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    subnets = ec2.describe_subnets(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc]},
            {"Name": "map-public-ip-on-launch", "Values": ["true"]},
        ]
    )["Subnets"]
    subnet_ids = [item["SubnetId"] for item in sorted(subnets, key=lambda s: s["AvailabilityZone"])]
    if len(subnet_ids) < 2:
        raise SystemExit("Need at least two public subnets for the load balancer.")
    return vpc, subnet_ids[:6]


def _sg_id(ec2, vpc: str, group_name: str) -> str | None:
    found = ec2.describe_security_groups(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc]},
            {"Name": "group-name", "Values": [group_name]},
        ]
    )["SecurityGroups"]
    return found[0]["GroupId"] if found else None


def ensure_security_groups(ec2, vpc: str) -> tuple[str, str]:
    alb_name = f"{NAME}-alb"
    task_name = f"{NAME}-tasks"
    alb_id = _sg_id(ec2, vpc, alb_name)
    if alb_id is None:
        alb_id = ec2.create_security_group(
            GroupName=alb_name,
            Description="Idea Diligence public ALB",
            VpcId=vpc,
        )["GroupId"]
        _log(f"Created ALB security group {alb_id}")
    task_id = _sg_id(ec2, vpc, task_name)
    if task_id is None:
        task_id = ec2.create_security_group(
            GroupName=task_name,
            Description="Idea Diligence Fargate tasks",
            VpcId=vpc,
        )["GroupId"]
        _log(f"Created task security group {task_id}")
    for group_id, source in (
        (
            alb_id,
            {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
        ),
        (
            task_id,
            {
                "IpProtocol": "tcp",
                "FromPort": CONTAINER_PORT,
                "ToPort": CONTAINER_PORT,
                "UserIdGroupPairs": [{"GroupId": alb_id}],
            },
        ),
    ):
        try:
            ec2.authorize_security_group_ingress(GroupId=group_id, IpPermissions=[source])
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "InvalidPermission.Duplicate":
                raise
    return alb_id, task_id


def ensure_alb(elbv2, vpc: str, subnet_ids: list[str], alb_sg: str) -> tuple[str, str, str]:
    existing = elbv2.describe_load_balancers()["LoadBalancers"]
    alb = next((item for item in existing if item["LoadBalancerName"] == f"{NAME}-alb"), None)
    if alb is None:
        alb = elbv2.create_load_balancer(
            Name=f"{NAME}-alb",
            Subnets=subnet_ids[:6],
            SecurityGroups=[alb_sg],
            Scheme="internet-facing",
            Type="application",
            IpAddressType="ipv4",
        )["LoadBalancers"][0]
        _log("Created application load balancer")
    alb_arn = alb["LoadBalancerArn"]
    dns = alb["DNSName"]

    groups = elbv2.describe_target_groups()["TargetGroups"]
    tg = next((item for item in groups if item["TargetGroupName"] == f"{NAME}-tg"), None)
    if tg is None:
        tg = elbv2.create_target_group(
            Name=f"{NAME}-tg",
            Protocol="HTTP",
            Port=CONTAINER_PORT,
            VpcId=vpc,
            TargetType="ip",
            HealthCheckPath="/api/health",
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=2,
            UnhealthyThresholdCount=3,
            Matcher={"HttpCode": "200"},
        )["TargetGroups"][0]
        _log("Created target group")
    tg_arn = tg["TargetGroupArn"]

    listeners = elbv2.describe_listeners(LoadBalancerArn=alb_arn)["Listeners"]
    if not listeners:
        elbv2.create_listener(
            LoadBalancerArn=alb_arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[{"Type": "forward", "TargetGroupArn": tg_arn}],
        )
        _log("Created HTTP listener")
    return alb_arn, tg_arn, dns


def execution_role_arn(iam) -> str:
    try:
        return iam.get_role(RoleName="ecsTaskExecutionRole")["Role"]["Arn"]
    except ClientError:
        return iam.get_role(RoleName="ecsInstanceRole")["Role"]["Arn"]


def register_task(ecs, iam, image: str, api_key: str) -> str:
    role_arn = execution_role_arn(iam)
    response = ecs.register_task_definition(
        family=NAME,
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        cpu="1024",
        memory="2048",
        executionRoleArn=role_arn,
        containerDefinitions=[
            {
                "name": NAME,
                "image": image,
                "essential": True,
                "portMappings": [{"containerPort": CONTAINER_PORT, "protocol": "tcp"}],
                "environment": [
                    {"name": "HOST", "value": "0.0.0.0"},
                    {"name": "PORT", "value": str(CONTAINER_PORT)},
                    {"name": "DEFAULT_MODEL_PROVIDER", "value": "gemini"},
                    {"name": "DEFAULT_MODEL_ID", "value": "gemini-3.6-flash"},
                    {"name": "GEMINI_API_KEY", "value": api_key},
                ],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": f"/ecs/{NAME}",
                        "awslogs-region": REGION,
                        "awslogs-stream-prefix": "ecs",
                    },
                },
            }
        ],
    )
    arn = response["taskDefinition"]["taskDefinitionArn"]
    _log(f"Registered {arn}")
    return arn


def ensure_cluster(ecs) -> None:
    names = [item.split("/")[-1] for item in ecs.list_clusters()["clusterArns"]]
    if CLUSTER not in names:
        ecs.create_cluster(clusterName=CLUSTER)
        _log(f"Created cluster {CLUSTER}")


def ensure_service(ecs, task_arn: str, subnet_ids: list[str], task_sg: str, tg_arn: str) -> None:
    services = ecs.list_services(cluster=CLUSTER)["serviceArns"]
    exists = any(item.endswith(f"/{NAME}") for item in services)
    network = {
        "awsvpcConfiguration": {
            "subnets": subnet_ids[:3],
            "securityGroups": [task_sg],
            "assignPublicIp": "ENABLED",
        }
    }
    load_balancers = [
        {
            "targetGroupArn": tg_arn,
            "containerName": NAME,
            "containerPort": CONTAINER_PORT,
        }
    ]
    if exists:
        ecs.update_service(
            cluster=CLUSTER,
            service=NAME,
            taskDefinition=task_arn,
            desiredCount=1,
            forceNewDeployment=True,
        )
        _log("Updated ECS service (forced new deployment)")
        return
    ecs.create_service(
        cluster=CLUSTER,
        serviceName=NAME,
        taskDefinition=task_arn,
        desiredCount=1,
        launchType="FARGATE",
        loadBalancers=load_balancers,
        networkConfiguration=network,
        healthCheckGracePeriodSeconds=90,
    )
    _log("Created ECS service")


def wait_healthy(elbv2, tg_arn: str, dns: str) -> str:
    url = f"http://{dns}"
    _log(f"Waiting for target health at {url} ...")
    deadline = time.time() + 600
    while time.time() < deadline:
        desc = elbv2.describe_target_health(TargetGroupArn=tg_arn)
        states = [item["TargetHealth"]["State"] for item in desc.get("TargetHealthDescriptions", [])]
        _log(f"  targets: {states or ['none yet']}")
        if states and all(state == "healthy" for state in states):
            return url
        time.sleep(15)
    raise SystemExit(f"Timed out waiting for healthy targets. Check {url} in a few minutes.")


def main() -> int:
    session = boto3.Session(region_name=REGION)
    api_key = gemini_key()
    ecr = session.client("ecr")
    ecs = session.client("ecs")
    ec2 = session.client("ec2")
    elbv2 = session.client("elbv2")
    logs = session.client("logs")
    iam = session.client("iam")

    uri = ensure_ecr(ecr)
    image = push_image(ecr, uri)
    ensure_logs(logs)
    vpc, subnet_ids = default_network(ec2)
    alb_sg, task_sg = ensure_security_groups(ec2, vpc)
    _alb_arn, tg_arn, dns = ensure_alb(elbv2, vpc, subnet_ids, alb_sg)
    ensure_cluster(ecs)
    task_arn = register_task(ecs, iam, image, api_key)
    ensure_service(ecs, task_arn, subnet_ids, task_sg, tg_arn)
    url = wait_healthy(elbv2, tg_arn, dns)
    _log("")
    _log(f"Public demo URL: {url}")
    _log("Load demo dossier is instant. Live investigation takes 3-6 minutes.")
    (REPO_ROOT / ".deploy-url").write_text(url + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
