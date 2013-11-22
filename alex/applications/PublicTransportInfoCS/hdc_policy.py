#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import random

import autopath

from alex.components.dm import DialoguePolicy
from alex.components.slu.da import DialogueAct, DialogueActItem
# from alex.components.slu.da import DialogueActConfusionNetwork
# from alex.components.asr.utterance import Utterance, UtteranceNBList, UtteranceConfusionNetwork

from datetime import timedelta
from .directions import GooglePIDDirectionsFinder
from .weather import OpenWeatherMapWeatherFinder
from datetime import datetime
from datetime import time as dttime


def randbool(n):
    if random.randint(1, n) == 1:
        return True

    return False


class PTICSHDCPolicy(DialoguePolicy):
    """The handcrafted policy for the PTI-CS system."""

    def __init__(self, cfg, ontology):
        super(PTICSHDCPolicy, self).__init__(cfg, ontology)

        self.directions = GooglePIDDirectionsFinder(cfg=cfg)
        self.weather = OpenWeatherMapWeatherFinder(cfg=cfg)

        self.das = []
        self.last_system_dialogue_act = None

        self.debug = cfg['DM']['basic']['debug']
        self.session_logger = cfg['Logging']['session_logger']
        self.system_logger = cfg['Logging']['system_logger']
        self.policy_cfg = self.cfg['DM']['dialogue_policy']['PTICSHDCPolicy']
        self.accept_prob = self.policy_cfg['accept_prob']

    def reset_on_change(self, ds, changed_slots):
        """Reset slots which depends on changed slots.

        :param ds: dialogue state
        :param changed_slots: slots changed in the last turn
        """
        for ds_slot in ds:
            for changed_slot in changed_slots:
                if self.ontology.reset_on_change(ds_slot, changed_slot):
                    if isinstance(ds[ds_slot], float):
                        ds[ds_slot] = 0.0
                    elif isinstance(ds[ds_slot], int):
                        ds[ds_slot] = 0.0
                    elif isinstance(ds[ds_slot], basestring):
                        ds[ds_slot] = "none"
                    else:
                        ds[ds_slot].reset()

                    self.system_logger.debug("Reset on change: {slot} because of {changed_slot}".format(slot=ds_slot,
                                                                                                        changed_slot=changed_slot))
                    break

    def get_da(self, dialogue_state):
        """The main policy decisions are made here. For each action, some set of conditions must be met. These
         conditions depends on the action.

        :param dialogue_state: the belief state provided by the tracker
        :return: a dialogue act - the system action
        """

        ludait_prob, ludait  = dialogue_state["ludait"].mph()
        if ludait_prob < self.policy_cfg['accept_prob_ludait']:
            ludait = 'none'

        # all slots being requested by the user
        slots_being_requested = dialogue_state.get_slots_being_requested(self.policy_cfg['accept_prob_being_requested'])
        # all slots being confirmed by the user
        slots_being_confirmed = dialogue_state.get_slots_being_confirmed(self.policy_cfg['accept_prob_being_confirmed'])
        # all slots supplied by the user but not implicitly confirmed
        noninformed_slots = dialogue_state.get_slots_being_noninformed(self.policy_cfg['accept_prob_noninformed'])
        # all slots deemed to be accepted
        accepted_slots = dialogue_state.get_accepted_slots(self.accept_prob)
        # all slots that should be confirmed
        slots_tobe_confirmed = dialogue_state.get_slots_tobe_confirmed(self.policy_cfg['confirm_prob'], self.accept_prob)
        # all slots for which the policy can use ``select`` DAI
        slots_tobe_selected = dialogue_state.get_slots_tobe_selected(self.policy_cfg['select_prob'])
        # all slots changed by a user in the last turn
        changed_slots = dialogue_state.get_changed_slots(self.policy_cfg['change_prob'])


        if self.debug:
            s = []
            s.append('PTICSHDCPolicy - Slot stats')
            s.append("")
            s.append("ludait:                 %s" % unicode(ludait))
            s.append("Slots being requested:  %s" % unicode(slots_being_requested))
            s.append("Slots being confirmed:  %s" % unicode(slots_being_confirmed))
            s.append("Non-informed slots:     %s" % unicode(noninformed_slots))
            s.append("")
            s.append("Accepted slots:         %s" % unicode(accepted_slots))
            s.append("Slots to be confirmed:  %s" % unicode(slots_tobe_confirmed))
            s.append("Slots to be selected:   %s" % unicode(slots_tobe_selected))
            s.append("Changed slots:          %s" % unicode(changed_slots))
            s = '\n'.join(s)

            self.system_logger.debug(s)

        # output DA
        res_da = None

        # reset all slots depending on changed slots
        self.reset_on_change(dialogue_state, changed_slots)

        # topic-independent behavior
        if dialogue_state.turn_number > self.cfg['PublicTransportInfoCS']['max_turns']:
            # Hang up if the talk has been too long
            res_da = DialogueAct('bye()&inform(toolong="true")')

        elif len(self.das) == 0:
            # NLG("Dobrý den. Jak Vám mohu pomoci")
            res_da = DialogueAct("hello()")

        elif ludait == "silence":
            # at this moment the silence and the explicit null act
            # are treated the same way: NLG("")
            silence_time = dialogue_state['silence_time']

            if silence_time > self.cfg['DM']['basic']['silence_timeout']:
                res_da = DialogueAct('inform(silence_timeout="true")')
            else:
                res_da = DialogueAct("silence()")
            dialogue_state["ludait"].reset()

        elif ludait == "bye":
            # NLG("Na shledanou.")
            res_da = DialogueAct("bye()")
            dialogue_state["ludait"].reset()

        elif ludait == "null" or ludait == "other":
            # NLG("Sorry, I did not understand. You can say...")
            res_da = DialogueAct("notunderstood()")
            res_da.extend(self.get_limited_context_help(dialogue_state))
            dialogue_state["ludait"].reset()

        elif ludait == "help":
            # NLG("Pomoc.")
            res_da = DialogueAct("help()")
            dialogue_state["ludait"].reset()

        elif ludait == "thankyou":
            # NLG("Díky.")
            res_da = DialogueAct('inform(cordiality="true")&hello()')
            dialogue_state["ludait"].reset()

        elif ludait == "restart":
            # NLG("Dobře, zančneme znovu. Jak Vám mohu pomoci?")
            dialogue_state.restart()
            res_da = DialogueAct("restart()&hello()")
            dialogue_state["ludait"].reset()

        elif ludait == "repeat":
            # NLG - use the last dialogue act
            res_da = DialogueAct("irepeat()")
            dialogue_state["ludait"].reset()

        elif slots_tobe_selected:
            # select between two values for a slot that is not certain
            res_da = self.select_info(slots_tobe_confirmed)

        elif slots_tobe_confirmed:
            # confirm all slots that are not certain
            res_da = self.confirm_info(slots_tobe_confirmed)

        elif 'current_time' in slots_being_requested:
            # Respond to questions about current weather
            # TODO: allow combining with other questions?
            res_da = self.req_current_time()

        # topic-dependent
        elif dialogue_state['lta_task'].test('weather', self.accept_prob):
            # talk about weather
            res_da = self.get_weather_res_da(dialogue_state, ludait, slots_being_requested, slots_being_confirmed,
                                             accepted_slots, changed_slots)
        else:
            # talk about public transport
            res_da = self.get_connection_res_da(dialogue_state, ludait, slots_being_requested, slots_being_confirmed,
                                                accepted_slots, changed_slots)

        self.last_system_dialogue_act = res_da

        # record the system dialogue acts
        self.das.append(self.last_system_dialogue_act)
        return self.last_system_dialogue_act

    def get_connection_res_da(self, ds, ludait, slots_being_requested, slots_being_confirmed, accepted_slots, changed_slots):
        """Handle the public transport connection dialogue topic.

        :param ds: The current dialogue state
        :param requested_slots: The slots currently requested by the user
        :rtype: DialogueAct
        """

        # output DA
        res_da = None

        if ludait == "reqalts":
            # NLG("There is nothing else in the database.")
            # NLG("The next connection is ...")
            res_da = self.get_an_alternative(ds)
            ds["ludait"].reset()

        elif "alternative" in accepted_slots:
            # Search for traffic direction and/or present the requested
            # directions already found
            res_da = self.get_requested_alternative(ds)
            ds["alternative"].reset()

        elif slots_being_requested:
            # inform about all requested slots
            res_da = self.get_requested_info(slots_being_requested, ds, accepted_slots)

        elif slots_being_confirmed:
            # inform about all slots being confirmed by the user
            res_da = self.get_confirmed_info(slots_being_confirmed, ds)

        else:
            # implicitly confirm all changed slots
            res_da = self.get_iconfirm_info(changed_slots)
            # request all unknown information
            req_da = self.request_more_info(ds, accepted_slots)
            if len(req_da) == 0:
                # we know everything we need -> start searching
                res_da.extend(self.get_directions(ds, check_conflict=True))
            else:
                res_da.extend(req_da)
        return res_da

    def get_weather_res_da(self, ds, ludait, slots_being_requested, slots_being_confirmed, accepted_slots, changed_slots):
        """Handle the dialogue about weather.

        :param ds: The current dialogue state
        :param requested_slots: The slots currently requested by the user
        :rtype: DialogueAct
        """
        # get dialogue state values
        weather_time = ds['weather_time'].mpv()
        weather_time_rel = ds['weather_time_rel'].mpv()
        date_rel = ds['date_rel'].mpv()
        ampm = ds['ampm'].mpv()
        time = ds['time'].mpv()
        time_rel = ds['time_rel'].mpv()

        print "#81", weather_time, weather_time_rel, date_rel, ampm, time, time_rel

        # interpret time
        time_abs = weather_time if weather_time != 'none' else time
        time_rel = weather_time_rel if weather_time_rel != 'none' else time_rel
        daily = (time_abs == 'none' and time_rel == 'none' and
                 ampm == 'none' and date_rel != 'none')
        # check if any time is set to distinguish current/prediction
        weather_time_int = None
        if time_abs != 'none' or time_rel != 'none' or ampm != 'none' or date_rel != 'none':
            weather_time_int = self.interpret_time(time_abs, ampm, time_rel, date_rel)
        # request the weather
        weather = self.weather.get_weather(weather_time_int, daily)
        # return the result
        res_da = DialogueAct()
        # time
        if weather_time_int:
            if time_rel != 'none':
                res_da.append(DialogueActItem('inform', 'weather_time_rel', time_rel))
            elif time_abs != 'none' or ampm != 'none':
                res_da.append(DialogueActItem('inform', 'weather_time',
                                              '%d:%02d' % (weather_time_int.hour, weather_time_int.minute)))
            if date_rel != 'none':
                res_da.append(DialogueActItem('inform', 'date_rel', date_rel))
        else:
            res_da.append(DialogueActItem('inform', 'time_rel', 'now'))
        # temperature
        if not daily:
            res_da.append(DialogueActItem('inform', 'temperature', str(weather.temp)))
        else:
            res_da.append(DialogueActItem('inform', 'min_temperature', str(weather.min_temp)))
            res_da.append(DialogueActItem('inform', 'max_temperature', str(weather.max_temp)))
        # weather conditions
        res_da.append(DialogueActItem('inform', 'weather_condition', weather.condition))
        return res_da

    def get_an_alternative(self, ds):
        """Return an alternative route, if there is one, or ask for
        origin stop if there has been no route searching so far.

        :param ds: The current dialogue state
        :rtype: DialogueAct
        """
        if 'route_alternative' not in ds:
            return DialogueAct('request(from_stop)')
        else:
            ds['route_alternative'] += 1
            ds['route_alternative'] %= len(ds.directions) if ds.directions is not None else 1
            return self.get_directions(ds)

    def get_requested_alternative(self, ds):
        """Return the requested route (or inform about not finding one).

        :param ds: The current dialogue state
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        if 'route_alternative' in ds:
            ds_alternative = ds["alternative"].mpv()

            if ds_alternative == "last":
                res_da.extend(self.get_directions(ds, "last"))
            elif ds_alternative == "next":
                ds["route_alternative"] += 1

                if ds['route_alternative'] == len(ds.directions):
                    ds["route_alternative"] -= 1
                    res_da.append(DialogueActItem("inform", "found_directions", "no_next"))
                else:
                    res_da.extend(self.get_directions(ds, "next"))

            elif ds_alternative == "prev":
                ds["route_alternative"] -= 1

                if ds["route_alternative"] == -1:
                    ds["route_alternative"] += 1
                    res_da.append(DialogueActItem("inform", "found_directions", "no_prev"))
                else:
                    res_da.extend(self.get_directions(ds, "prev"))

            else:
                ds["route_alternative"] = int(ds_alternative) - 1
                res_da.extend(self.get_directions(ds))

        else:
            res_da.append(DialogueActItem("inform", "stops_conflict", "no_stops"))

        return res_da

    def get_requested_info(self, requested_slots, ds, accepted_slots):
        """Return a DA containing information about all requested slots.

        :param ds: The current dialogue state
        :param requested_slots: A dictionary with keys for all requested \
                slots and the correct return values.
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        for slot in requested_slots:
            if ds['route_alternative'] != "none":
                if slot == 'from_stop':
                    res_da.extend(self.req_from_stop(ds))
                elif slot == 'to_stop':
                    res_da.extend(self.req_to_stop(ds))
                elif slot == 'departure_time':
                    res_da.extend(self.req_departure_time(ds))
                elif slot == 'departure_time_rel':
                    res_da.extend(self.req_departure_time_rel(ds))
                elif slot == 'arrival_time':
                    res_da.extend(self.req_arrival_time(ds))
                elif slot == 'arrival_time_rel':
                    res_da.extend(self.req_arrival_time_rel(ds))
                elif slot in 'duration':
                    res_da.extend(self.req_duration(ds))
                elif slot == "num_transfers":
                    res_da.extend(self.req_num_transfers(ds))
            else:
                if slot in ['from_stop', 'to_stop',
                            'departure_time', 'departure_time_rel',
                            'arrival_time', 'arrival_time_rel',
                            'duration', 'num_transfers', ]:
                    dai = DialogueActItem("inform", "stops_conflict", "no_stops")
                    res_da.append(dai)

                    if 'from_stop' not in accepted_slots:
                        dai = DialogueActItem("help", "inform", "from_stop")
                        res_da.append(dai)
                    elif 'to_stop' not in accepted_slots:
                        dai = DialogueActItem("help", "inform", "to_stop")
                        res_da.append(dai)
                else:
                    dai = DialogueActItem("inform", slot, requested_slots[slot])
                    res_da.append(dai)
                    ds["rh_" + slot].reset()

            ds["rh_" + slot].reset()

        return res_da

    def get_confirmed_info(self, confirmed_slots, ds, accepted_slots):
        """Return a DA containing information about all slots being confirmed
        by the user (confirm/deny).

        Update the current dialogue state regarding the information provided.

        *WARNING* This confirms only against values in the dialogue state, however, it should (also in some cases)
        confirm against the results obtained from database, e.g. departure_time slot.

        :param ds: The current dialogue state
        :param confirmed_slots: A dictionary with keys for all slots \
                being confirmed, along with their values
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        for slot in confirmed_slots:
            if confirmed_slots[slot].mpv() == ds[slot].mpv():
                # it is as user expected
                res_da.append(DialogueActItem("affirm"))
                dai = DialogueActItem("inform", slot, ds[slot].mpv())
                res_da.append(dai)
            else:
                # it is something else than what user expected
                res_da.append(DialogueActItem("negate"))
                dai = DialogueActItem("deny", slot, ds["ch_" + slot].mpv())
                res_da.append(dai)

                if slot in accepted_slots:
                    dai = DialogueActItem("inform", slot, ds[slot].mpv())
                    res_da.append(dai)

            ds["ch_" + slot].reset()

        return res_da

    def confirm_info(self, tobe_confirmed_slots):
        """Return a DA containing confirming only one slot from the slot to be confirmed .

        :param tobe_confirmed_slots: A dictionary with keys for all slots \
                that should be confirmed, along with their values
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        for slot in tobe_confirmed_slots:
            if 'system_confirms' in self.ontology['slot_attributes'][slot]:
                dai = DialogueActItem("confirm", slot, tobe_confirmed_slots[slot].mpv())
                res_da.append(dai)
                #confirm explicitly only one slot at the time
                break
        return res_da

    def select_info(self, tobe_selected_slots):
        """Return a DA containing select act for two most probable values of only one slot
        from the slot to be used for select DAI.

        :param tobe_selected_slots: A dictionary with keys for all slots \
                which the two most probable values should be selected
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        for slot in tobe_selected_slots:
            if 'system_selects' in self.ontology['slot_attributes'][slot]:
                val1, val2 = tobe_selected_slots[slot].tmpvs()
                res_da.append(DialogueActItem("select", slot, val1))
                res_da.append(DialogueActItem("select", slot, val2))
                #select values only in one slot at the time
                break
        return res_da

    def get_iconfirm_info(self, changed_slots):
        """Return a DA containing all needed implicit confirms.

        Implicitly confirm all slots provided but not yet confirmed.

        This include also slots changed during the conversation.

        :param changed_slots: A dictionary with keys for all slots \
                that have not been implicitly confirmed, along with \
                their values
        :rtype: DialogueAct
        """
        res_da = DialogueAct()

        if changed_slots:
            iconf_da = DialogueAct()
            for slot in changed_slots:
                if 'system_iconfirms' in self.ontology['slot_attributes'][slot]:
                    dai = DialogueActItem("iconfirm", slot, changed_slots[slot].mpv())
                    iconf_da.append(dai)
            res_da.extend(iconf_da)
        return res_da

    def request_more_info(self, ds, accepted_slots):
        """Return a DA requesting further information needed to search
        for traffic directions, or perform the search if no further information
        is needed.

        :param ds: The current dialogue state
        :rtype: DialogueAct
        """
        req_da = DialogueAct()

        # check all state variables and the output one request dialogue act
        # it just easier to have a list than a tree, the tree is just to confusing for me. FJ
        if 'from_stop' not in accepted_slots and \
                'to_stop' not in accepted_slots and \
                ('departure_time' not in accepted_slots or
                 'time' not in accepted_slots) and \
                randbool(10):
            req_da.extend(DialogueAct('request(departure_time)'))
        elif 'from_stop' not in accepted_slots and \
                ('centre_direction' not in accepted_slots or
                ds['centre_direction'].most_probable_value() == '*') and \
                randbool(9):
            req_da.extend(DialogueAct('confirm(centre_direction="from")'))
        elif 'to_stop' not in accepted_slots and \
                ('centre_direction' not in accepted_slots or
                ds['centre_direction'].most_probable_value() == '*') and \
                randbool(8):
            req_da.extend(DialogueAct('confirm(centre_direction="to")'))
        elif 'from_stop' not in accepted_slots and \
                'to_stop' not in accepted_slots and \
                randbool(3):
            req_da.extend(DialogueAct("request(from_stop)&request(to_stop)"))
        elif 'from_stop' not in accepted_slots:
            req_da.extend(DialogueAct("request(from_stop)"))
        elif 'to_stop' not in accepted_slots:
            req_da.extend(DialogueAct('request(to_stop)'))

        return req_da

    def req_current_time(self):
        """Generates a dialogue act informing about the current time.
        :rtype: DialogueAct
        """
        cur_time = datetime.now()
        return DialogueAct('inform(current_time=%d:%02d)' % (cur_time.hour, cur_time.minute))

    def req_from_stop(self, ds):
        """Generates a dialogue act informing about the origin stop of the last
        recommended connection.

        TODO: this gives too much of information. Maybe it would be worth to split this into more dialogue acts
          and let user ask for all individual pieces of information. The good thing would be that it would lead
          to longer dialogues.

        :rtype : DialogueAct
        """
        route = ds.directions.routes[ds['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in leg.steps:
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'from_stop', step.departure_stop))
                da.append(DialogueActItem('inform', 'vehicle', step.vehicle))
                da.append(DialogueActItem('inform', 'line', step.line_name))
                da.append(DialogueActItem('inform', 'headsign', step.headsign))
                return da

    def req_to_stop(self, ds):
        """Return a DA informing about the destination stop of the last
        recommended connection.
        """
        route = ds.directions.routes[ds['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in reversed(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'to_stop', step.arrival_stop))
                return da

    def req_departure_time(self, dialogue_state):
        """Generates a dialogue act informing about the departure time from the origin stop of the last
        recommended connection.

        :rtype : DialogueAct
        """
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in leg.steps:
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'from_stop', step.departure_stop))
                da.append(DialogueActItem('inform', 'departure_time', step.departure_time.strftime("%H:%M")))
                return da

    def req_departure_time_rel(self, dialogue_state):
        """Return a DA informing the user about the relative time until the
        last recommended connection departs.
        """
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in leg.steps:
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'from_stop', step.departure_stop))
                # construct relative time from now to departure
                departure_time_rel = (step.departure_time - datetime.now()).seconds / 60
                departure_time_rel_hrs, departure_time_rel_mins = divmod(departure_time_rel, 60)
                da.append(DialogueActItem('inform', 'departure_time_rel',
                                          '%d:%02d' % (departure_time_rel_hrs, departure_time_rel_mins)))
                return da

    def req_arrival_time(self, dialogue_state):
        """Return a DA informing about the arrival time the destination stop of the last
        recommended connection.
        """
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in reversed(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'to_stop', step.arrival_stop))
                da.append(DialogueActItem('inform', 'arrival_time', step.arrival_time.strftime("%H:%M")))
                return da

    def req_arrival_time_rel(self, dialogue_state):
        """Return a DA informing about the relative arrival time the destination stop of the last
        recommended connection.
        """
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in reversed(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'to_stop', step.arrival_stop))
                # construct relative time from now to arrival
                arrival_time_rel = (step.arrival_time - datetime.now()).seconds / 60
                arrival_time_rel_hrs, arrival_time_rel_mins = divmod(arrival_time_rel, 60)
                da.append(DialogueActItem('inform', 'arrival_time_rel',
                                          '%d:%02d' % (arrival_time_rel_hrs, arrival_time_rel_mins)))
                return da

    def req_duration(self, dialogue_state):
        """Return a DA informing about journey time to the destination stop of the last
        recommended connection.
        """
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in leg.steps:
            if step.travel_mode == step.MODE_TRANSIT:
                departure_time = step.departure_time
                break
        else:
            return None

        for step in reversed(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                arrival_time = step.arrival_time
                break
        else:
            return None

        duration = (arrival_time - departure_time).seconds / 60
        duration_hrs, duration_mins = divmod(duration, 60)
        da.append(DialogueActItem('inform', 'duration', '%d:%02d' % (duration_hrs, duration_mins)))
        return da

    def req_num_transfers(self, dialogue_state):
        """Return a DA informing the user about the number of transfers in the
        last recommended connection.
        """
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]
        leg = route.legs[0]
        n = sum([1 for step in leg.steps if step.travel_mode == step.MODE_TRANSIT]) - 1
        da = DialogueAct('inform(num_transfers="%d")' % n)
        return da

    def get_directions(self, ds, route_type='true', check_conflict=False):
        """Retrieve Google directions, save them to dialogue state and return
        corresponding DAs.

        Responsible for the interpretation of AM/PM time expressions.

        :param ds: The current dialogue state
        :param route_type: a label for the found route (to be passed on to \
                :func:`say_directions`)
        :param check_conflict: If true, will check if the origin and \
                destination stops are different and issue a warning DA if not.
        :rtype: DialogueAct
        """
        # check for route conflicts
        from_stop_val = ds['from_stop'].mpv()
        to_stop_val = ds['to_stop'].mpv()

        if check_conflict and from_stop_val == to_stop_val:
            apology_da = DialogueAct()
            apology_da.extend(DialogueAct('apology()'))
            apology_da.extend(DialogueAct('inform(stops_conflict="thesame")'))
            apology_da.extend(DialogueAct("inform(from_stop='%s')" % from_stop_val))
            apology_da.extend(DialogueAct("inform(to_stop='%s')" % to_stop_val))
            return apology_da

        # get dialogue state values
        departure_time = ds['departure_time'].mpv()
        departure_time_rel = ds['departure_time_rel'].mpv()
        arrival_time = ds['arrival_time'].mpv()
        arrival_time_rel = ds['arrival_time_rel'].mpv()
        date_rel = ds['date_rel'].mpv()
        ampm = ds['ampm'].mpv()
        time = ds['time'].mpv()
        time_rel = ds['time_rel'].mpv()

        # interpret departure and arrival time
        departure_time_int, arrival_time_int = None, None
        if arrival_time != 'none' or arrival_time_rel != 'none':
            arrival_time_int = self.interpret_time(arrival_time, ampm, arrival_time_rel, date_rel)
        else:
            time_abs = departure_time if departure_time != 'none' else time
            time_rel = departure_time_rel if departure_time_rel != 'none' else time_rel
            departure_time_int = self.interpret_time(time_abs, ampm, time_rel, date_rel)

        # retrieve Google directions
        ds.directions = self.directions.get_directions(from_stop=from_stop_val,
                                                       to_stop=to_stop_val,
                                                       departure_time=departure_time_int,
                                                       arrival_time=arrival_time_int)
        return self.say_directions(ds, route_type)

    ORIGIN = 'ORIGIN'
    DESTIN = 'FINAL_DEST'

    def say_directions(self, dialogue_state, route_type):
        """Return DAs for the directions in the current dialogue state."""
        if not isinstance(dialogue_state['route_alternative'], int):
            dialogue_state['route_alternative'] = 0

        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]

        # only 1 leg should be present in case we have no waypoints
        steps = route.legs[0].steps

        res = []

        # introduction
        if len(dialogue_state.directions) > 1:
            res.append('inform(found_directions="%s")' % route_type)
            if route_type != "last":
                res.append("inform(alternative=%d)" % (dialogue_state['route_alternative'] + 1))

        # route description
        prev_arrive_stop = self.ORIGIN  # remember previous arrival stop
        for step_ndx, step in enumerate(steps):

            # find out what will be the next departure stop (needed later)
            next_leave_stop = self.DESTIN
            if step_ndx < len(steps) - 2 and \
                    steps[step_ndx + 1].travel_mode == step.MODE_WALKING:
                next_leave_stop = steps[step_ndx + 2].departure_stop
            elif step_ndx < len(steps) - 1 and \
                    steps[step_ndx + 1].travel_mode == step.MODE_TRANSIT:
                next_leave_stop = steps[step_ndx + 1].departure_stop

            # walking
            if step.travel_mode == step.MODE_WALKING:
                # walking to stops with different names
                if (next_leave_stop == self.DESTIN and
                    prev_arrive_stop != dialogue_state['to_stop']) or \
                        (prev_arrive_stop == self.ORIGIN and
                         next_leave_stop != dialogue_state['from_stop']) or \
                        (next_leave_stop != self.DESTIN and
                         prev_arrive_stop != self.ORIGIN and
                         next_leave_stop != prev_arrive_stop):
                    # walking destination: next departure stop
                    res.append("inform(walk_to=%s)" % next_leave_stop)
                    res.append("inform(duration=0:%02d)" % (step.duration / 60))
            # public transport
            elif step.travel_mode == step.MODE_TRANSIT:
                res.append("inform(vehicle=%s)" % step.vehicle)
                res.append("inform(line=%s)" % step.line_name)
                res.append("inform(departure_time=%s)" %
                           step.departure_time.strftime("%H:%M"))
                # only mention departure if it differs from previous arrival
                if step.departure_stop != prev_arrive_stop:
                    res.append("inform(enter_at=%s)" % step.departure_stop)
                res.append("inform(headsign=%s)" % step.headsign)
                res.append("inform(exit_at=%s)" % step.arrival_stop)
                # only mention transfer if there is one
                if next_leave_stop != self.DESTIN:
                    res.append("inform(transfer='true')")
                prev_arrive_stop = step.arrival_stop

        # no route found: apologize
        if len(res) == 0:
            res.append('apology()')
            res.append("inform(from_stop='%s')" % dialogue_state['from_stop'].mpv())
            res.append("inform(to_stop='%s')" % dialogue_state['to_stop'].mpv())

        res_da = DialogueAct("&".join(res))

        return res_da

    DEFAULT_AMPM_TIMES = {'morning': "06:00",
                          'am': "10:00",
                          'pm': "15:00",
                          'evening': "18:00",
                          'night': "00:00"}

    def interpret_time(self, time_abs, time_ampm, time_rel, date_rel):

        # interpret dialogue state time
        now = datetime.now()

        # relative time
        if (time_abs == 'none' and time_ampm == 'none') or time_rel != 'none':
            time_abs = now
            if time_rel not in ['none', 'now']:
                trel_parse = datetime.strptime(time_rel, "%H:%M")
                time_abs += timedelta(hours=trel_parse.hour, minutes=trel_parse.minute)
        # absolute time
        else:
            if time_abs == 'none' and time_ampm != 'none':
                time_abs = self.DEFAULT_AMPM_TIMES[time_ampm]
            time_parsed = datetime.combine(now, datetime.strptime(time_abs, "%H:%M").time())
            time_hour = time_parsed.hour
            now_hour = now.hour
            # handle 12hr time
            if time_hour >= 1 and time_hour <= 12:
                # interpret AM/PM
                if time_ampm != 'none':
                    # 'pm' ~ 12pm till 11:59pm
                    if time_ampm == 'pm' and time_hour < 12:
                        time_hour += 12
                    # 'am'/'morning' ~ 12am till 11:59am
                    elif time_ampm in ['am', 'morning'] and time_hour == 12:
                        time_hour = 0
                    # 'evening' ~ 4pm till 3:59am
                    elif time_ampm == 'evening' and time_hour >= 4:
                        time_hour = (time_hour + 12) % 24
                    # 'night' ~ 6pm till 5:59am
                    elif time_ampm == 'night' and time_hour >= 6:
                        time_hour = (time_hour + 12) % 24
                # 12hr time + no AM/PM set: default to next 12hrs
                elif now_hour > time_hour and now_hour < time_hour + 12:
                    time_hour = (time_hour + 12) % 24
            time_abs = datetime.combine(now, dttime(time_hour, time_parsed.minute))
            # ds['time_abs'] = "%d:%.2d" % (time_abs.hour, time_abs.minute)

        # relative date
        if date_rel == 'tomorrow':
            time_abs += timedelta(days=1)
        elif date_rel == 'day_after_tomorrow':
            time_abs += timedelta(days=2)
        elif time_abs < now:
            time_abs += timedelta(days=1)

        return time_abs

    def get_limited_context_help(self, dialogue_state):
        res_da = DialogueAct()

        # if we do not understand the input then provide the context sensitive help
        if not 'route_alternative' in dialogue_state:
            # before something is offered
            if randbool(10):
                res_da.append(DialogueActItem("help", "inform", "hangup"))
            elif randbool(9):
                res_da.append(DialogueActItem("help", "request", "help"))
            elif randbool(8):
                res_da.append(DialogueActItem("help", "inform", "departure_time"))
            elif randbool(7):
                res_da.append(DialogueActItem("help", "repeat"))
            elif not dialogue_state['from_stop'].test("none", self.accept_prob, neg_val=True):
                res_da.append(DialogueActItem("help", "inform", "from_stop"))
            elif not dialogue_state['to_stop'].test("none", self.accept_prob, neg_val=True):
                res_da.append(DialogueActItem("help", "inform", "to_stop"))
        else:
            # we already offered a connection
            if randbool(4):
                res_da.append(DialogueActItem("help", "inform", "alternative_last"))
            elif randbool(7):
                res_da.append(DialogueActItem("help", "inform", "alternative_next"))
            elif randbool(6):
                res_da.append(DialogueActItem("help", "inform", "alternative_prev"))
            elif randbool(5):
                res_da.append(DialogueActItem("help", "inform", "alternative_abs"))
            elif randbool(4):
                res_da.append(DialogueActItem("help", "request", "from_stop"))
            elif randbool(3):
                res_da.append(DialogueActItem("help", "request", "to_stop"))
            elif randbool(2):
                res_da.append(DialogueActItem("help", "request", "num_transfers"))

        return res_da
