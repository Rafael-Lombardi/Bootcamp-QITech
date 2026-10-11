from tests.utils import INTERNAL_TOKEN
from tests.utils.requisition import ClientRequisition


def test_sample_entity_routes_are_disabled():
    for method, endpoint in (
        ("POST", "/sample_entity"),
        ("GET", "/sample_entity/example"),
        ("GET", "/sample_entities"),
        ("PUT", "/sample_entity/example"),
        ("PUT", "/webhook/sample_entity/example/increment_counter"),
    ):
        response = ClientRequisition.send(
            method,
            endpoint,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        assert response.response_status == 404
        assert response.response_json["code"] == "QIT000404"
