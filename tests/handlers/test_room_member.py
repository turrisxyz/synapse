from unittest.mock import patch

from twisted.test.proto_helpers import MemoryReactor

from synapse.api.constants import Membership
from synapse.api.errors import LimitExceededError
import synapse.rest.admin
import synapse.rest.client.login
import synapse.rest.client.room
from synapse.server import HomeServer
from synapse.types import UserID, create_requester
from synapse.util import Clock

from tests.unittest import HomeserverTestCase, override_config


class TestJoinsLimitedByPerRoomRateLimiter(HomeserverTestCase):
    servlets = [
        synapse.rest.admin.register_servlets,
        synapse.rest.client.login.register_servlets,
        synapse.rest.client.room.register_servlets,
    ]

    def prepare(self, reactor: MemoryReactor, clock: Clock, hs: HomeServer) -> None:
        self.handler = hs.get_room_member_handler()

        # Create three users.
        self.alice = self.register_user("alice", "pass")
        self.alice_token = self.login("alice", "pass")
        self.bob = self.register_user("bob", "pass")
        self.bob_token = self.login("bob", "pass")
        self.chris = self.register_user("chris", "pass")
        self.chris_token = self.login("chris", "pass")

        # Create a room on this homeserver.
        # Note that this counts as a
        self.room_id = self.helper.create_room_as(self.alice, tok=self.alice_token)

    @override_config({"rc_joins_per_room": {"per_second": 0, "burst_count": 2}})
    def test_local_joins_contribute_to_limit_and_are_limited(self) -> None:
        # The rate limiter has accumulated one token from Alice's join after the create
        # event.
        #
        # Try joining the room as Bob.
        self.get_success(
            self.handler.update_membership(
                requester=create_requester(self.bob),
                target=UserID.from_string(self.bob),
                room_id=self.room_id,
                action=Membership.JOIN,
            )
        )

        # The rate limiter bucket is full. A second join should be denied.
        self.get_failure(
            self.handler.update_membership(
                requester=create_requester(self.chris),
                target=UserID.from_string(self.chris),
                room_id=self.room_id,
                action=Membership.JOIN,
            ),
            LimitExceededError,
        )

    @override_config({"rc_joins_per_room": {"per_second": 1, "burst_count": 1}})
    def test_remote_joins_are_limited(self) -> None:
        # Fill the rate limiter bucket so that subsequent requests will be denied

        # Ask to join a room on another server
        ...

    @override_config({"rc_joins_per_room": {"per_second": 1, "burst_count": 1}})
    def test_local_joins_contribute_to_rate_limit(self) -> None:
        ...

    @override_config({"rc_joins_per_room": {"per_second": 1, "burst_count": 1}})
    def test_remote_joins_contribute_to_rate_limit(self) -> None:
        ...
