"""
404 FOUNDERS — gRPC Servicer Verification Tests
Verifies NeuralInferenceServicer, ClusterTelemetryServicer, and TaskDispatchServicer.
"""

import pytest
from api.grpc.service import (
    ClusterTelemetryServicer,
    NeuralInferenceServicer,
    TaskDispatchServicer,
)
from api.rest.app import initialize_runtime_services


@pytest.fixture(scope="module")
def services():
    return initialize_runtime_services()


def test_grpc_cluster_telemetry_servicer():
    servicer = ClusterTelemetryServicer()
    vitals = servicer.GetClusterVitals(tier_name="tier_a")
    assert vitals.status == "OPERATIONAL"
    assert vitals.total_gpus > 0
    assert vitals.total_nodes > 0


def test_grpc_neural_inference_servicer(services):
    inference_eng = services.get("inference_engine")
    servicer = NeuralInferenceServicer(inference_engine=inference_eng)

    chunks = list(servicer.GenerateTokens(token_ids=[1, 2, 3], max_new_tokens=4))
    assert len(chunks) == 4
    assert chunks[-1].is_finished is True
    assert chunks[0].logprob == -0.1


def test_grpc_task_dispatch_servicer():
    servicer = TaskDispatchServicer()
    resp = servicer.DispatchTask(
        task_id="TASK-001",
        task_type="PRETRAINING_STEP",
        parameters={"learning_rate": 0.0003, "batch_size": 8},
    )
    assert resp["task_id"] == "TASK-001"
    assert resp["status"] == "ACCEPTED"
    assert "node" in resp["assigned_node"]
