# !/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'NereWARin'

import Team
import util
import DataStoring as db
from Leagues import League, TeamResult
import Match as M
from values import Coefficients as C
from operator import attrgetter, itemgetter
import random
import time
import os
import warnings
import copy

# c = Leagues.League("a", "a", [])
class Cup(League):
    """
    represents Cup, some methods from League were overridden
    """
    def __init__(self, name, season, members, delta_coefs, pair_mode = 1, seeding = "A1_B16",
                 state_params = ("final_stage", ), save_to_db = True, prefix = ""):
        """

        :param name:
        :param season:

        # ACTUAL REVERSED ORDER !!!
        :param members: should be in seeding order (1place_team, 2place_team...) . net will ve provided by that class itself

        :param seeding: if Cup used as qualification for UEFA (or another special tournament),
        seeding must be a list in of dicts {round : int, seeded_teams : count, toss = ("all_rnd") or
        ("not_same_country", "not_played_group") as in UEFA Champ League

        :param delta_coefs:
        :param pair_mode: 0 - one match in pair, 1 - home & guest but the final , 2 - always home & guest
        :return:
        """
        if prefix:
            if not isinstance(seeding, list):
                raise Exception, "seeding must be a list of dicts roundN:[seeded_teams]"
        else:
            if seeding not in self.getSeedings():
                raise Exception, "call independed Cup but seeding type not found in provided list getSeedings()"

        # super(self.__class__, self).__init__(tournament, season, members, delta_coefs)#(self, tournament, season, members, delta_coefs)
        # super(Cup, self).__init__(tournament, season, members, delta_coefs, state_params)#(self, tournament, season, members, delta_coefs)
        super(Cup, self).__init__(name, season, members, delta_coefs, pair_mode, seeding, state_params)
        self.pair_mode = pair_mode

        # self.results - empty list. after run() it will be filled as following:
        # [team_champion, team_finished_in_final, teams_finished_in_semi-final, ... , teams_finished_in_qualRoundn, ...
        # teams_finished_in_qualRound1# ]
        print "\nWELCOME TO CUP ***", name.upper(), season, "***"

        state = {st:None for st in state_params}

        for member in self.members:
            self.results.append(TeamResult(member, state).get4table())
        # print "self.results", self.results
        # initialize net
        # self.seeding = copy.copy(seeding)
        self.seeding = seeding

        # {round: [ (t1,t2,pair_result, m1, m2) ... } , ... roundFinal : [ ... ]
        self.round_names = "not computed" # TODO make branch: get from params (if external scheme exists) OR compute in run()

        # self.net = {"not implemented yet" : None} # TODO net should be ini as start pos (1 round) and seeding (branch), then in run - updated from results
        # TODO its not necessacy for cups with
        self.net = {} #
        # *** HEART OF RUN METHOD ***
        #   ***                 ***
        # CALL HELPER FUNCTIONS
        # if seeding == "rnd" or "A1_F16":
        # try:
        #     # print "teams_num", teams_num
        #     self.p_rounds, self.q_rounds = self.rounds_count(teams_num)#self.rounds_count(teams_num)
        #     # print "self.p_rounds %s, self.q_rounds %s" % (self.p_rounds, self.q_rounds)
        # except:
        #     print "%s. need more teams to run cup" % teams_num
        #     raise AttributeError
        # else:
        #     # convert number of round to round tournament (1/4, semi-final, etc.)
        #     self.round_names = self.roundNames(self.p_rounds, self.q_rounds)
        #     # print round_names
        #     all_rounds = self.p_rounds + self.q_rounds
        #
        #     pteamsI, qpairs = PQplaces(self.p_rounds, self.q_rounds)


    def __str__(self):
        string = ""
        for k, v in self.net.iteritems():
            string += str(k) + ":" + str(v) + "\n"
            # print "k", k
            # string += self.round_names[k] + ":" + str(v) + "\n"
        return string

    def getNet(self):
        """
        for print or display in web, has format self.net[round].append((pair[0].getName(), pair[1].getName(), results))
        where result can be (0:0) or ((1:1), (2:2)) - # TODO CHECK BY TEST

        :return:
        """
        return self.net

    def getSeedings(self):
        """
        seeding mode is by what rule pairs form
        return a tuple of the standart seeding behaviours, bur external scheme is allowed
        :return: available seeding modes supported by class
        """
        return (
            "David&Goliaf", # BEST RATING vs WORST RATING. in every round first index of remaining teams vs last index of remaining teams
            "rnd", # first index of remaining teams - with random choice of the rest rem.teams
            #  TODO implement all of this by adding winners and external quilified treems by external seedings
            "A1_B16" # hardcoded rule: winner of pair A1-B16 will play with winner of A16-B1 and etc.
        )

    def rounds_count(self, teams_num):
        """
         define rounds count
        """
        if teams_num < 1:
            raise Exception, "no teams to run cup"
        if teams_num < 2:
            warnings.warn("RUN CUP %s FOR ONE TEAM %s") % (self.name, self.getMember(0).getName())
            return 0, 0
        # remaining teams number
        rem_tn = teams_num / 2.0

        # play-off rounds num
        p_rounds = 1
        while rem_tn >= 2:
            rem_tn = rem_tn / 2
            p_rounds += 1

        # qualification rounds num
        q_rounds = 0
        if rem_tn != 1.0:
            q_rounds += 1
        return p_rounds, q_rounds

    def roundNames(self, p_rounds, q_rounds):
        """
        generate round names to store and print
        (convert last round to final, last-1 to semifinal, etc.)
        :param p_rounds: number playoff rounds                  #!# starts from round 1
        :param q_rounds: numbers of qualification rounds        #!# starts from round 1
        :return:
        """
        rounds = p_rounds + q_rounds
        names = {}
        # print "we have %s rounds in Cup %s (%s in qualification, %s in playoff" % (rounds, self.getName(), q_rounds, p_rounds)

        names[rounds] = "Final"
        names[rounds-1] = "Semi-Final"

        for round in range(q_rounds + 1, rounds-1):
            names[round] = "1/%s-Final" % (2**(rounds-round))

        names[q_rounds] = "Qualification Play-Off"
        for round in range(1, q_rounds):
            names[round] = "Qualification round %s" % round

        return names

    def run(self, print_matches = False):
        """
        generate matches, every match team rating and result updates
        after all, table updates and returns
        """
        teams = list(self.getMember())
        teams_num = len(teams)
        # clear results
        self.results = {}
        self.net = {}

        # seeding "A1_B16"
        # 14-team cup example

        # play-off                                          *
        # round 1 (final)                   *                                 *
        # round 2 (semi-final)      *                *               *                 *
        # round 3 (1/4 final)    1     8         4      5         2      7         3      6
        # qualification
        # round 4 (qual 1)            8 9       4 13   5 12             7 10      3 14   6 11
        # // number = index in members + 1

        # TODO save PQplaces in table for Cup-tournament. if not exists, compute it

        # TODO save rounds tournament from rounds num for every Cup-tournament.

        def PQplaces(p_rounds, q_rounds):
            """
            p_rounds - number of play-off rounds in cup
            q_rounds - number of qualification rounds in cup

            return:
            qteams - number of teams played in qualification round, if q_rounds = 1
            pteam_num - number of teams witch start from playoff
            qpairs - number of pairs in qualification round
            """
            if  q_rounds != 1:
                raise NotImplemented, "for now it can be used only for national Cup that has at most 1 qual round "
            # teams in lowest play-off round
            pteam_num = 2 ** p_rounds
            # pais in highest qualification round
            qpairs = teams_num - pteam_num
            # indexes of teams that seeds directly in playoff
            borderI = pteam_num - qpairs
            qteams = qpairs * 2
            # return borderI, qpairs
            return qteams

        def cupRound(_teams_, round, pair_mode, toss, print_matches = False):
            """
            teams - only those teams that will play in that round

            """
            # rem_teams = list(teams)
            teams = list(_teams_)
            loosers = []
            winners = []
             # it may be match or doublematch, so struggle is a common tournament for it
            struggles = len(teams)/2
            matches = struggles * (pair_mode + 1)

            # cause its Cup!
            playoff = True

            if pair_mode: # Two Matches in struggle
                classname = M.DoubleMatch
            else:
                classname = M.Match

            # create record of round
            self.net[round] = []

            for struggleN in range(struggles):
                team1 = teams.pop(0) # favorite
                if toss == "David&Goliaf":
                    team2 = teams.pop() # outsider
                elif toss == "rnd":
                    # TODO fix wild random! or at leat keep track of it to build self.net...
                    # TODO team0 will play with rnd team of the weak half
                    teams_num = len(teams)
                    team2 = teams.pop(random.randrange(teams_num/2, teams_num)) # outsider
                elif toss == "A1_B16":
                    print "check A1_B16 correctness - now its same as David&Goliaf - who lies?!!"
                    team2 = teams.pop()
                elif toss == "not_same_country_and_played_in_group":
                    # for 1/4 Champions League
                    team2 = teams[-1]

                    def played_in_group(team1, team2):
                        pass
                        columns = ["id_tournament", "round", "id_team1", "id_team2"]
                        id_tournament = self.name
                        round = "" # TODO  CONSISTS GROUP !!!!!
                        values = [id_tournament, round, team1.getID(), team2.getID()]
                        # TODO SQL select id from %s where        db.MATCHES_TABLE

                    while team1.getCountry() == team2.getCountry() or played_in_group:
                        team2 = teams[random.randrange(teams_num/2, teams_num)]

                else:
                    raise Exception, "unknown toss parameter %s" % toss
                # if round_name not in self.net.keys():
                #     self.net[round_name]
                #     [1]
                # self.net[round_name[1]] =
                # warnings.warn("write ...to self.net")

                pair = (team1, team2)
                if random.randint(0,1): # TODO if pair_mode < 1, need to compute what team played less matches at home
                    pair = (team2, team1)

                # print "%s :  %s" % (team1, team2)
                # match_name = "%s %s. round %s. struggle %s"  \
                round_name = self.round_names[round]
                match_name = "%s %s. %s.%s"  \
                                % (self.getName(), self.season, round_name, struggleN)
                struggle = classname(pair, self.delta_coefs, match_name, playoff)
                struggle.run()
                # print "classname %s" % classname
                results = struggle.getResult(1, 2, casted=True)

                # for res in results:
                #     print "res", res

                # TODO use ORM to draw net better
                # self.net[round].append((pair, results))
                self.net[round].append((pair[0].getName(), pair[1].getName(), results))

                # print "results", results, [res for res in results]
                # print "result %s" % result
                if print_matches:
                    print struggle

                looser = struggle.getLooser()
                loosers.append(looser)

                winner = struggle.getWinner()
                winners.append(winner)

            # if print_matches:
            #    print "%s struggles (%s matches) were played" % (struggles, matches)

            return loosers, winners

        def RunRoundAndUpdate(round, pair_mode, results, teams, toss):
            # try:
            #
            # except:
            #     pass
            # round_name = self.getRoundNames()[round]

            # # create new list for pair in round
            # self.net[round] = []

            loosers, winners = cupRound(teams, round, pair_mode, toss, print_matches)

            # UPDATE RESULTS
            # TODO choose results form and net form
            # self.results.append(loosers)
            res = dict(results)
            res[round] = loosers

            # if print_matches:
            #     for stage, result in enumerate(self.results):
            #         print "results (loosers) of stage %s len of %s : %s" % (stage, len(self.results[stage]), [team.getName() for team in self.results[stage]])

            # return results, teams
            return res, loosers, winners


        def get_pairmode(round):
            """
            check if final round to switch to 1 match in pair
            """
            if round == self.all_rounds and self.pair_mode == 1:
                print "switch pair_mode from 1 to 0 so it will be only one final match!"
                pairmode = 0 # ONE MATCH FOR FINAL
            else:
                pairmode = self.pair_mode
            return pairmode




            # TODO: to support self.q_rounds > 1, need recompute qpairs and qteamsI with special logic: compute by
            # TODO: rounds_count only if external schema does't exists (else get it from additional class parameters,
            # TODO: UEFA is good example of that situation)


        try:
            # print "teams_num", teams_num
            # borderI - number of teams that skip first qualification round
            if isinstance(self.seeding, str):
                # national Cups
                self.p_rounds, self.q_rounds = self.rounds_count(teams_num)#self.rounds_count(teams_num)
                borderI = PQplaces(self.p_rounds, self.q_rounds)
                round_info = None
                toss = self.seeding
                # print "self.p_rounds %s, self.q_rounds %s" % (self.p_rounds, self.q_rounds)

            elif isinstance(self.seeding, list):
                self.q_rounds = len(self.seeding)
                self.p_rounds = 0
                round = 0
                round_info = self.seeding[round]
                borderI = round_info["count"]
                toss = round_info["toss"]
            else:
                raise ValueError, "unsupported argument type for seeding %s" %type(self.seeding)
            self.all_rounds = self.p_rounds + self.q_rounds

        except:
            print "%s. need more teams to run cup" % teams_num
            raise AttributeError
        else:
            # convert number of round to round tournament (1/4, semi-final, etc.)
            self.round_names = self.roundNames(self.p_rounds, self.q_rounds)

            # print round_names

            winners = []

            # Qualification
            for round in range(1, self.all_rounds + 1):

                seeded = teams[-borderI:]
                _teams = [self.getMember(i) for i in seeded] + winners
                pair_mode = get_pairmode(round)
                self.results, loosers, winners = RunRoundAndUpdate(round, pair_mode, self.results, _teams, toss)
                # UPDATE LIST OF REMAINING TEAMS
                teams = teams - _teams

                if round_info:
                    round_info = self.seeding[round]
                    borderI = round_info["count"]
                    toss = round_info["toss"]
                else:
                    # national
                    borderI = 0
                    # after 1 round no more seeded teams, only winners of prev round
                    # toss = self.seeding




            # # if not isinstance(self.seeding, str):
            # #     # UEFA
            # #     raise NotImplemented, "implement CL and EL seeding"
            # #
            # # else:
            # #     # national
            # #     if self.seeding == "A1_B16":
            # #         seeded = teams[borderI:]
            # #     else:
            # #         print "basic seeding (=%s) Cup with at most 1 qual. round" % self.seeding
            # #         seeded = teams[borderI:]
            #
            # # id of winners that will be played in next round (exclusive of already seeding)
            # winners = []
            # # MIXES ROUNDS
            # rounds =  self.p_rounds + self.q_rounds
            # for round in range(1, rounds + 1):
            #     if not isinstance(self.seeding, str):
            #         # UEFA
            #         # raise NotImplemented, "implement CL and EL seeding"
            #         borderI = 0
            #     else:
            #         # national
            #         borderI = self.seeding[round]
            #     # get teams from from head
            #     seeded = teams[borderI:]
            #     print "teams", teams
            #
            #     # cut copy of teams to get indexes from head in future correctly
            #     teams -=  seeded
            #     print "rest teams", teams
            #
            #     # print "len(teams) = %s", len(teams)
            #     # print "q_round", q_round
            #     teams_idxs = winners + seeded
            #
            #     if round == rounds and self.pair_mode == 1:
            #         # FINAL
            #         pairmode = 0
            #         self.results, loosers, winners = RunRoundAndUpdate(round, pairmode, self.results, teams_idxs)
            #     else:
            #         self.results, loosers, winners = RunRoundAndUpdate(round, self.pair_mode, self.results, teams_idxs)


            #
            #
            # # PLAY-OFF
            # for round in range(self.q_rounds + 1, all_rounds):
            #     # print "len(teams) = %s", len(teams)
            #     # round_name = round_names[round]
            #     self.results, loosers, winners = RunRoundAndUpdate(round, self.pair_mode, self.results, teams)
            #     for looser in loosers:
            #         teams.remove(looser)
            #
            # # FINAL
            # #     print "final round!"
            # # print "len(teams) = %s", len(teams)
            # if self.pair_mode == 1:
            #     # if print_matches:
            #     #     print "switch pair_mode from 1 to 0 so it will be only one final match!"
            #     pairmode = 0 # ONE MATCH FOR FINAL
            # else:
            #     pairmode = self.pair_mode
            # # round_name = round_names[all_rounds]
            # self.results, loosers, winners = RunRoundAndUpdate(all_rounds, pairmode, self.results, teams)
            # for looser in loosers:
            #     teams.remove(looser)


            # else:
            #     self.results, teams = RunRoundAndUpdate(all_rounds + 1, self.pair_mode, self.results, teams)

            # assert len(teams) == 1, "Cup ends with more than one winner!"
            if not self.prefix:
                assert len(winners) == 1, "Cup ends with more than one winner!"
                self.winner = winners.pop()
            else:
                # for qualificaton for example
                self.winner = winners

            # # print result for EVERY round
            # if print_matches:
            #     for stage, result in enumerate(self.results):
            #         print "results (loosers) of stage %s len of %s : %s" % (stage, len(self.results[stage]), [team.getName() for team in self.results[stage]])

            # TODO save Cup in database probe
            self.saveToDB(self.net)
            return self.winner


    def saveToDB(self, net):
        """
        save Cup data to database
        :param: net is a dict round:[teams]
        """

        if not self.prefix:
            # unregistered yet - for national Leagues
            self.saveTounramentPlayed()
        # else get from parameter - if its Group Tourn
        id_tournament = self.name

        columns = db.select(table_names=db.TOURNAMENTS_RESULTS_TABLE, fetch="colnames", where = " LIMIT 0")[1:]
        # TODO edit getName to return readable info about tournament: readable name and season
        print "\nsaving tournament %s results to database in columns %s" % (self.getName(), columns)
        count = 0
        for round, teams in self.net.iteritems():
            # pos = self.prefix +
            pos = self.round_names[round]
            for team in teams:
                id_team = team.getName()
                values = [id_tournament, pos, id_team]
                db.insert(db.TOURNAMENTS_RESULTS_TABLE, columns, values)
                count += 1
        # print "inserted %s rows to %s" % (len(self.net.values()), db.TOURNAMENTS_RESULTS_TABLE)
        print "inserted %s rows to %s" % (count, db.TOURNAMENTS_RESULTS_TABLE)


    def getRoundNames(self):
        return self.round_names

    def getWinner(self):
        return self.winner

    def test(self, print_matches = False, print_ratings = False):

        print "\nTEST CUP CLASS\n"
        print "pair_mode = %s\nseeding = %s\n" % (self.pair_mode, self.seeding)
        print "initial Net:"
        print self#.printTable()
        if print_matches:
            print "\nMatches:"
        self.run(print_matches)
        print "\nWinner:\n%s" % self.getWinner()
        # print "\nresults:\n%s" % [(k, [team.getName() for team in self.results[k]] ) for k in self.results.keys()]
        print "\nresults:"
        for k in self.results.keys():
            # TODO sort results by round (maybe store them in list)
            print k, [team.getName() for team in self.results[k]]
        print "\nFinal Net:\n", str(self), "\n"

        # ratings after league
        # print "print_ratings = %s" % print_ratings
        # print "self.getMember() %s" % self.getMember()
        if print_ratings:
            for team in self.getMember():
                print team.getName(), team.getRating()



# class Net():
#     """
#     represents Net for printing in Gui
#     """
#     def __init__(self):
#         self.net = {}
#
#     def __str__(self):
#         return sorted(  self.net)


# TEST
if __name__ == "__main__":
    @util.timer
    def Test(*args, **kwargs):
        # VERSION = "v1.1"
        with open(os.path.join("", 'VERSION')) as version_file:
            values_version = version_file.read().strip()
        coefs = C(values_version).getRatingUpdateCoefs("list")

        teams = []
        team_num = kwargs["team_num"]
        for i in range(team_num):
            teamN = i + 1
            rating = team_num - i
            uefa_pos = teamN
            teams.append(Team.Team("FC team%s" % teamN, "RUS", rating, "Команда%s" % teamN, uefa_pos))

        # TEST CUP CLASS
        if "Cup" in args:

            # for seeding in Cup.getSeedings(Cup):
            #     print seeding
            for pair_mode in [0,1,2]:
                # pair_mode = 0 # one match
                # pair_mode = 1 # home + guest every match but the final
                # pair_mode = 2 # home + guest every match

                # print_matches = False
                print_matches = True

                print_ratings = False
                # print_ratings = True

                s =  Cup("no Cup, just getSeedings", "", teams, coefs, pair_mode)
                seedings = s.getSeedings()
                # print "seedings", seedings
                for seeding in seedings:
                    # print seeding , "seeding"
                    # print "teams, coefs, pair_mode, seeding", teams, coefs, pair_mode, seeding
                    tstcp = Cup("testCup", "2015/2016", teams, coefs, pair_mode, seeding)
                    tstcp.test(print_matches, print_ratings)
                # # Cup("testCup", "2015/2016", teams, coefs, pair_mode).run()


    Test("Cup", team_num = 20)