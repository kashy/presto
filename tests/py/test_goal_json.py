from __future__ import print_function, unicode_literals

import json
from decimal import Decimal

from gittip.testing import Harness
from gittip.models.participant import Participant


class Tests(Harness):

    def make_alice(self):
        return self.make_participant('alice', claimed_time='now')

    def change_goal(self, goal, goal_custom="", username="alice", expecting_error=False):
        if isinstance(username, Participant):
            username = username.username
        elif username == 'alice':
            self.make_alice()

        method = self.client.POST if not expecting_error else self.client.PxST
        response = method( "/alice/goal.json"
                         , {'goal': goal, 'goal_custom': goal_custom}
                         , auth_as=username
                          )
        return response


    def test_participant_can_set_their_goal_to_null(self):
        response = self.change_goal("null")
        actual = json.loads(response.body)['goal']
        assert actual == None

    def test_participant_can_set_their_goal_to_zero(self):
        response = self.change_goal("0")
        actual = json.loads(response.body)['goal']
        assert actual == "0.00"

    def test_participant_can_set_their_goal_to_a_custom_amount(self):
        response = self.change_goal("custom", "100.00")
        actual = json.loads(response.body)['goal']
        assert actual == "100.00"

    def test_custom_amounts_can_include_comma(self):
        response = self.change_goal("custom", "1,100.00")
        actual = json.loads(response.body)['goal']
        assert actual == "1,100.00"

    def test_wonky_custom_amounts_are_standardized(self):
        response = self.change_goal("custom", ",100,100.00000")
        actual = json.loads(response.body)['goal']
        assert actual == "100,100.00"

    def test_anonymous_gets_404(self):
        response = self.change_goal("100.00", username=None, expecting_error=True)
        assert response.code == 404, response.code

    def test_invalid_is_400(self):
        response = self.change_goal("cheese", expecting_error=True)
        assert response.code == 400, response.code

    def test_invalid_custom_amount_is_400(self):
        response = self.change_goal("custom", "cheese", expecting_error=True)
        assert response.code == 400, response.code


    # Exercise the event logging for goal changes.

    def test_last_goal_is_stored_in_participants_table(self):
        alice = self.make_alice()
        self.change_goal("custom", "100", alice)
        self.change_goal("custom", "200", alice)
        self.change_goal("custom", "300", alice)
        self.change_goal("null", "", alice)
        self.change_goal("custom", "400", alice)
        actual = self.db.one("SELECT goal FROM participants")
        assert actual == Decimal("400.00")

    def test_all_goals_are_stored_in_events_table(self):
        alice = self.make_alice()
        self.change_goal("custom", "100", alice)
        self.change_goal("custom", "200", alice)
        self.change_goal("custom", "300", alice)
        self.change_goal("null", "", alice)
        self.change_goal("custom", "400", alice)
        actual = self.db.all("SELECT (payload->'values'->>'goal')::int AS goal "
                             "FROM events ORDER BY ts DESC")
        assert actual == [400, None, 300, 200, 100, None]
