from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from datetime import datetime as dt
from datetime import timedelta as td
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import pandas as pd
import numpy as np
import configparser
import time
import calendar
import pymysql
import json


class DFS_Scraper:

    def __init__(self, config_file='config.txt'):

        # Load and read config
        self.config = configparser.RawConfigParser()
        self.config.read(config_file)

        # Create Chrome driver instance
        option = webdriver.ChromeOptions()
        option.add_argument(" — incognito")
        self.browser = webdriver.Chrome(ChromeDriverManager().install())

    def quit(self):
        self.browser.quit()
        
    def navigate(self, where):
        if where == 'salaries':
            self.browser.get('https://www.fantasypros.com/daily-fantasy/nfl/draftkings-salary-changes.php')
            # close the message about cookies
            self.browser.find_element_by_class_name('onetrust-close-btn-handler.onetrust-close-btn-ui.banner-close-button.ot-close-icon').click()
        elif where == 'props':
            self.browser.get('https://sportsbook.draftkings.com/featured')
            featured = self.browser.find_element_by_class_name('sportsbook-expandable-shell__wrapper')
            for element in featured.find_elements_by_class_name('sportsbook-navigation-item-link.sportsbook-navigation-item-link--league'):
                if 'NFL' in element.find_element_by_class_name('sportsbook-navitation-item-title-text').text:
                    element.click()
        elif where == 'fantasy':
            self.browser.get("https://fantasy.espn.com/football/players/projections")
            # defaults to 'This Week','Full Projections', and 'All' positions - need to change here
            time.sleep(1)
            self.browser.find_element_by_class_name('Button.Button--filter.player--filters__projections-button').click()
            

    def get_player_salary(self, position):
        # click on desired position
        positions = self.browser.find_element_by_class_name('pills.pos-filter.pull-left').find_elements_by_tag_name('li')
        for pos in positions:
            if position in pos.text:
                pos.click()
        # orgaized by change from last week, want by this week salary so click on salary twice
        headers = self.browser.find_elements_by_tag_name('th')
        headers[4].find_element_by_class_name('tablesorter-header-inner').click()
        headers[4].find_element_by_class_name('tablesorter-header-inner').click()
        
        to_return = []
        
        data = self.browser.find_element_by_tag_name('table').find_element_by_tag_name('tbody')
        for row in data.find_elements_by_class_name(position):
            to_return.append([x.text for x in row.find_elements_by_tag_name('td')])
        
        return(pd.DataFrame(data = {'ECR': [x[0] for x in to_return],
                             'Player': [x[1] for x in to_return],
                             'Kickoff': [x[2] for x in to_return],
                             'Opponent': [x[3] for x in to_return],
                             'This Week': [x[4] for x in to_return],
                             'Last Week': [x[5] for x in to_return],
                             'Difference': [x[6] for x in to_return]}))
    
    def get_player_props(self, prop_type):
        try:
            prop_categories = self.browser.find_element_by_class_name('sportsbook-responsive-card-container__header.sportsbook-custom-scrollbar-darkest')
            prop_categories.find_element_by_id(f'game_category_{prop_type}').click()
            time.sleep(2)
        except:
            if prop_type == 'TD Scorers':
                self.browser.get('https://sportsbook.draftkings.com/leagues/football/nfl?category=td-scorers&subcategory=anytime-td-scorer')
            elif prop_type == 'Passing Props':
                self.browser.get('https://sportsbook.draftkings.com/leagues/football/nfl?category=passing-props')
            elif prop_type == 'Rushing/Receiving Props':
                self.browser.get('https://sportsbook.draftkings.com/leagues/football/nfl?category=rush/rec-props')
                
        if prop_type == 'TD Scorers':
            to_return = []
            prev_len = 0
            curr_len = 0
            
            self.browser.find_element_by_id('subcategory_Anytime TD Scorer').click()
            games = self.browser.find_elements_by_class_name('sportsbook-event-accordion__wrapper.expanded')
            for game in self.browser.find_elements_by_class_name('sportsbook-event-accordion__wrapper.expanded'):
                game_data = game.find_element_by_class_name('sportsbook-event-accordion__accordion').get_attribute('data-tracking')
                players = game.find_elements_by_class_name('component-204__outcome-row')
                for player in players:
                    player_name = player.find_element_by_class_name('component-204__outcome-label').text
                    td_odds = player.find_element_by_class_name('sportsbook-odds.american.no-margin.default-color').text
                    to_return.append((json.loads(game_data)['value'], player_name, td_odds))
                    curr_len += 1
                if len(to_return) == prev_len:
                    players = game.find_elements_by_class_name('component-204-horizontal__outcome-row')
                    for player in players:
                        player_name = player.find_element_by_class_name('component-204-horizontal__outcome-label').text
                        td_odds = player.find_element_by_class_name('component-204-horizontal__cell').text
                        to_return.append((json.loads(game_data)['value'], player_name, td_odds))
                        curr_len += 1
                prev_len = curr_len
                    
            return(pd.DataFrame(data = {'Game': [x[0] for x in to_return],
                                        'Player': [x[1] for x in to_return],
                                        'TD Odds': [x[2] for x in to_return]}))
        
        elif prop_type == 'Passing Props':
            yards_info = []
            td_info = []
            int_info = []
            
            self.browser.find_element_by_id('subcategory_Pass Yds').click()
            time.sleep(1)
            for game in self.browser.find_elements_by_class_name('sportsbook-event-accordion__wrapper.expanded'):
                game_data = game.find_element_by_class_name('sportsbook-event-accordion__accordion').get_attribute('data-tracking')
                for player in game.find_element_by_class_name('sportsbook-event-accordion__children-wrapper').find_element_by_tag_name('table').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr'):
                    player_name = player.find_element_by_class_name('sportsbook-row-name').text
                    yds = player.find_elements_by_class_name('sportsbook-outcome-cell__line')[0].text
                    yards_info.append((json.loads(game_data)['value'], player_name, yds))
                
            self.browser.find_element_by_id('subcategory_Pass TDs').click()
            time.sleep(1)
            for game in self.browser.find_elements_by_class_name('sportsbook-event-accordion__wrapper.expanded'):
                game_data = game.find_element_by_class_name('sportsbook-event-accordion__accordion').get_attribute('data-tracking')
                for player in game.find_element_by_class_name('sportsbook-event-accordion__children-wrapper').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr'):
                    player_name = player.find_element_by_class_name('sportsbook-row-name').text
                    tds = player.find_elements_by_class_name('sportsbook-outcome-cell__line')[0].text
                    juice = player.find_elements_by_class_name('sportsbook-odds.american.default-color')[0].text
                    td_info.append((json.loads(game_data)['value'], player_name, tds, juice))
            
            try:
                self.browser.find_element_by_id('subcategory_Interceptions').click()
            except: # often can't find because need to scroll further right in props
                self.browser.find_element_by_class_name('sportsbook-tabbed-subheader').find_element_by_class_name('side-arrow.side-arrow--right').click()
                self.browser.find_element_by_id('subcategory_Interceptions').click()
            time.sleep(1)
            for game in self.browser.find_elements_by_class_name('sportsbook-event-accordion__wrapper.expanded'):
                game_data = game.find_element_by_class_name('sportsbook-event-accordion__accordion').get_attribute('data-tracking')
                for player in game.find_element_by_class_name('sportsbook-event-accordion__children-wrapper').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr'):
                    player_name = player.find_element_by_class_name('sportsbook-row-name').text
                    ints = player.find_elements_by_class_name('sportsbook-outcome-cell__line')[0].text
                    juice = player.find_element_by_class_name('sportsbook-odds.american.default-color').text
                    int_info.append((json.loads(game_data)['value'], player_name, ints, juice))
            
                  
            temp1 = pd.DataFrame(data = {'Game': [x[0] for x in yards_info],
                                 'Player': [x[1] for x in yards_info],
                                 'Passing Yards': [x[2] for x in yards_info]})
            temp2 = pd.DataFrame(data = {'Game': [x[0] for x in td_info],
                                 'Player': [x[1] for x in td_info],
                                 'Passing TDs': [x[2] for x in td_info],
                                 'TD Over Juice': [x[3] for x in td_info]})
            temp3 = pd.DataFrame(data = {'Game': [x[0] for x in int_info],
                                 'Player': [x[1] for x in int_info],
                                 'INTs': [x[2] for x in int_info],
                                 'INTs Over Juice': [x[3] for x in int_info]})

            return(temp1.merge(temp2, how = 'outer', on = ['Game','Player']).merge(temp3, how = 'outer', on = ['Game','Player']))

        
        elif prop_type == 'Rushing/Receiving Props' or 'Rush/Rec Props':
            rush_yards = []
            rec_yards = []
            receptions = []
            
            self.browser.find_element_by_id('subcategory_Rush Yds').click()
            time.sleep(1)
            for game in self.browser.find_elements_by_class_name('sportsbook-event-accordion__wrapper.expanded'):
                game_data = game.find_element_by_class_name('sportsbook-event-accordion__accordion').get_attribute('data-tracking')
                for player in game.find_element_by_class_name('sportsbook-event-accordion__children-wrapper').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr'):
                    player_name = player.find_element_by_class_name('sportsbook-row-name').text
                    yds = player.find_elements_by_class_name('sportsbook-outcome-cell__line')[0].text
                    rush_yards.append((json.loads(game_data)['value'], player_name, yds))
                    
            self.browser.find_element_by_id('subcategory_Rec Yds').click()
            time.sleep(1)
            for game in self.browser.find_elements_by_class_name('sportsbook-event-accordion__wrapper.expanded'):
                game_data = game.find_element_by_class_name('sportsbook-event-accordion__accordion').get_attribute('data-tracking')
                for player in game.find_element_by_class_name('sportsbook-event-accordion__children-wrapper').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr'):
                    player_name = player.find_element_by_class_name('sportsbook-row-name').text
                    tds = player.find_elements_by_class_name('sportsbook-outcome-cell__line')[0].text
                    rec_yards.append((json.loads(game_data)['value'], player_name, tds))
            
            self.browser.find_element_by_id('subcategory_Receptions').click()
            time.sleep(1)
            for game in self.browser.find_elements_by_class_name('sportsbook-event-accordion__wrapper.expanded'):
                game_data = game.find_element_by_class_name('sportsbook-event-accordion__accordion').get_attribute('data-tracking')
                for player in game.find_element_by_class_name('sportsbook-event-accordion__children-wrapper').find_element_by_tag_name('tbody').find_elements_by_tag_name('tr'):
                    player_name = player.find_element_by_class_name('sportsbook-row-name').text
                    tds = player.find_elements_by_class_name('sportsbook-outcome-cell__line')[0].text
                    juice = player.find_elements_by_class_name('sportsbook-odds.american.default-color')[0].text
                    receptions.append((json.loads(game_data)['value'], player_name, tds, juice))
                    
            temp1 = pd.DataFrame(data = {'Game': [x[0] for x in rush_yards],
                                 'Player': [x[1] for x in rush_yards],
                                 'Rushing Yards': [x[2] for x in rush_yards]})
            temp2 = pd.DataFrame(data = {'Game': [x[0] for x in rec_yards],
                                 'Player': [x[1] for x in rec_yards],
                                 'Rec Yards': [x[2] for x in rec_yards]})
            temp3 = pd.DataFrame(data = {'Game': [x[0] for x in receptions],
                                 'Player': [x[1] for x in receptions],
                                 'Receptions': [x[2] for x in receptions],
                                 'Receptions Over Juice': [x[3] for x in receptions]})
            
            return(temp1.merge(temp2, how = 'outer', on = ['Game','Player']).merge(temp3, how = 'outer', on = ['Game','Player']))
            
    def combine_props(self, td_odds, passing_info, rush_rec_info):
        # Do some calculations to prep for aggreagting expected production
        if not td_odds.empty:
            td_odds['ProbToScore'] = td_odds.apply(lambda row: implied_prob(row['TD Odds']), axis = 1)
        if not passing_info.empty:
            passing_info['ExpectedTdPasses'] = passing_info.apply(
                lambda row: expected_production(row['Passing TDs'], row['TD Over Juice']), axis = 1)
            passing_info['ExpectedInts'] = passing_info.apply(
                lambda row: expected_production(row['INTs'], row['INTs Over Juice']), axis = 1)
        if not rush_rec_info.empty:
            rush_rec_info['ExpectedRecs'] = rush_rec_info.apply(
            lambda row: expected_production(row['Receptions'], row['Receptions Over Juice']), axis = 1)
        
        if not passing_info.empty and not rush_rec_info.empty and not td_odds.empty:
            expected_player_output = passing_info.merge(rush_rec_info, how = 'outer', on = ['Game','Player']).merge(td_odds, how = 'left', on = ['Game','Player']).sort_values(['Game', 'Player'])
            expected_player_output['Passing Yards'] = pd.to_numeric(expected_player_output['Passing Yards'])
            expected_player_output['Rushing Yards'] = pd.to_numeric(expected_player_output['Rushing Yards'])
            expected_player_output['Rec Yards'] = pd.to_numeric(expected_player_output['Rec Yards'])
        elif not passing_info.empty and not rush_rec_info.empty:
            expected_player_output = passing_info.merge(rush_rec_info, how = 'outer', on = ['Game','Player'])
            expected_player_output['Passing Yards'] = pd.to_numeric(expected_player_output['Passing Yards'])
            expected_player_output['Rushing Yards'] = pd.to_numeric(expected_player_output['Rushing Yards'])
            expected_player_output['Rec Yards'] = pd.to_numeric(expected_player_output['Rec Yards'])
        elif not passing_info.empty and not td_odds.empty:
            expected_player_output = passing_info.merge(td_odds, how = 'left', on = ['Game','Player']).sort_values(['Game', 'Player'])
            expected_player_output['Passing Yards'] = pd.to_numeric(expected_player_output['Passing Yards'])
        elif not passing_info.empty:
            expected_player_output = passing_info
            expected_player_output['Passing Yards'] = pd.to_numeric(expected_player_output['Passing Yards'])
        else:
            return None


        expected_player_output['PredictedPropsBasedScore'] = expected_player_output.apply(lambda row: calculate_points(row), axis = 1)
        
        # reformat the game data so that it aligns with the salary data 
        games_simple = []

        for game in expected_player_output['Game']:
            teams = game.split(' @ ')
            away = teams[0].split(' ')[0]
            home = teams[1].split(' ')[0]
            if away in ['NY','LA']:
                away = away + teams[0].split(' ')[1][0]
            if home in ['NY','LA']:
                home = home + teams[1].split(' ')[1][0]
            game = f"{away} @ {home}"
            games_simple.append(game)

        expected_player_output['Game'] = games_simple

        return(expected_player_output)
    
    def get_fantasy_projections(self, position):
        position_selector = self.browser.find_elements_by_class_name('control.control--radio.picker-option')
        selected = None
        for p in position_selector:
            if p.text == position:
                selected = p
                p.click()
                time.sleep(1)
        assert selected != None, 'Incorrect Position Specified'
        
        data_table = self.browser.find_element_by_class_name('ResponsiveTable.ResponsiveTable--fixed-left.ResponsiveTable--fixed-right.players-table')
        tables = data_table.find_elements_by_tag_name('table')
        
        sort_points_button = tables[2].find_element_by_class_name('jsx-2810852873.table--cell.total.tar.header.sortable')
        self.browser.execute_script("arguments[0].click();", sort_points_button)
        time.sleep(1)
        ## check value in first row, if 0 then click again
        if tables[2].find_element_by_tag_name('tbody').find_element_by_tag_name('tr').text == '0.0':
            self.browser.execute_script("arguments[0].click();", sort_points_button)
            time.sleep(1)
            
        player_rows = tables[0].find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        players = []
        teams = []
        for row in player_rows:
            players.append(row.find_element_by_class_name('AnchorLink.link.clr-link.pointer').text)
            teams.append(row.find_element_by_class_name('playerinfo__playerteam').text)
        
        proj_rows = tables[2].find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
        projs = []
        for row in proj_rows:
            projs.append(row.text)
        
        if position == 'D/ST':
            to_return = pd.DataFrame(data = {'Player':players, 'Team':teams,'ESPNProj':projs})
            
        else:
            stat_rows = tables[1].find_element_by_tag_name('tbody').find_elements_by_tag_name('tr')
            pass_yards = []
            pass_tds = []
            pass_ints = []
            rush_yards = []
            rush_tds = []
            recs = []
            rec_yards = []
            rec_tds = []
            for row in stat_rows:
                data = row.find_elements_by_tag_name('td')
                pass_yards.append(data[1].text)
                pass_tds.append(data[2].text)
                pass_ints.append(data[3].text)
                rush_yards.append(data[5].text)
                rush_tds.append(data[6].text)
                recs.append(data[7].text)
                rec_yards.append(data[8].text)
                rec_tds.append(data[9].text)
            
            to_return = pd.DataFrame(data = {'Player':players, 'Team':teams, 'PassYards':pass_yards,
                                         'PassTDs':pass_tds, 'PassINTs':pass_ints, 'RushYards':rush_yards,
                                         'RushTDs':rush_tds, 'Recs':recs, 'RecYards':rec_yards,
                                         'RecTDs':rec_tds, 'ESPNProj':projs})
        return(to_return)
            
    
    def format_salary_data(self, df):
        games = []
        players = []
        salaries = []

        for _, row in df.iterrows():
            player = row['Player'].split(' (')[0]
            team = row['Player'].split(' (')[1].split(' ')[0]
            opponent = row['Opponent']

            if '@' in row['Opponent']:
                away = team
                home = row['Opponent'].replace('@','')
            else:
                away = row['Opponent']
                home = team
            game = f'{away} @ {home}'
            salary = row['This Week']
            games.append(game)
            players.append(player)
            salaries.append(pd.to_numeric(salary.replace('$','').replace(',','')))

        return(pd.DataFrame(data = {'Game': games, 'Player': players, 'Salary': salaries}))
    
    def combine_data(self, df1, df2, df3):
        # remove "II" as it is inconsistently used (will add more as they appear)
        df1['Player'] = df1['Player'].str.replace('II','').str.strip()
        df2['Player'] = df2['Player'].str.replace('II','').str.strip()
        df3['Player'] = df3['Player'].str.replace('II','').str.strip()
        
        # merge salary data and DraftKing projection based data
        temp = df1.merge(df2, how = 'left', on = ['Game','Player'])
        
        # calculate the dollars per DK props projection point
        dollars_per_dk_point = []
        for _, row in temp.iterrows():
            if not pd.isna(row['PredictedPropsBasedScore']):
                dollars_per_dk_point.append(row['Salary']/row['PredictedPropsBasedScore'])
            else:
                dollars_per_dk_point.append(None)
        temp['$/DKPoint'] = dollars_per_dk_point
        
        # get list of games and add to ESPN projections for joining
        games = get_games(df1)
        df3 = add_games(df3, games)
        
        # merge salary/DK data with ESPN projections
        temp2 = temp.merge(df3, how = 'left', on = ['Game','Player'])
        
        # calculate the dollars per ESPN projection point
        temp2['ESPNProj'] = pd.to_numeric(temp2['ESPNProj'])
        dollars_per_espn_point = []
        for _, row in temp2.iterrows():
            if not pd.isna(row['ESPNProj']) and row['ESPNProj'] != 0:
                dollars_per_espn_point.append(row['Salary']/row['ESPNProj'])
            else:
                dollars_per_espn_point.append(None)
        temp2['$/ESPNPoint'] = dollars_per_espn_point
        
        return(temp2)
    
    
        
##########
### Helper Functions    
##########
def implied_prob(odds):
    odds = odds.replace('+','')
    negative = 1
    if '−' in odds:
        negative = -1
        odds = odds.replace('−','')
    odds = int(odds)*negative
    if odds > 0:
        prob = 100/(odds+100)
    else:
        prob = (-1*odds)/((-1*odds)+100)
    return(prob)

def expected_production(line, odds):
    if pd.isna(line) or pd.isna(odds):
        return(None)
    line = pd.to_numeric(line)
    prob = implied_prob(odds)
    variation = prob - 0.5
    additional_production = variation*line
    return(line + additional_production)

def calculate_points(row):

    try:
        td_points  = 6*row['ProbToScore']
    except KeyError as e:
        td_points = 0
    try:
        td_pass_points = 4*row['ExpectedTdPasses']
    except:
        td_pass_pints = 0
    try:
        int_points = -1*row['ExpectedInts']
    except:
        int_points = 0
    try:
        pass_yards_points = row['Passing Yards']/25
    except:
        pass_yards_points = 0
    try:
        rush_yards_points = row['Rushing Yards']/10
    except:
        rush_yards_points = 0
    try:
        rec_yards_points = row['Rec Yards']/10
    except:
        rec_yards_points = 0
    try:
        recs_points = row['ExpectedRecs']
    except:
        recs_points = 0

    return np.nansum([td_points, td_pass_points, int_points, pass_yards_points, rush_yards_points, rec_yards_points, recs_points])

def get_games(df):
    games = df[['Game']]
    games['AwayTeam'] = [x[0] for x in games['Game'].str.split(' @ ')]
    games['HomeTeam'] = [x[1] for x in games['Game'].str.split(' @ ')]
    games = games.drop_duplicates()
    return(games)

def add_games(df, games):
    df['Team'] = df['Team'].str.replace('Wsh','Was').str.replace('Jax','Jac')
    games_to_add = []
    for _, row in df.iterrows():
        games_to_add.append(games[games['Game'].str.contains(row['Team'].upper())]['Game'].values[0])
    df['Game'] = games_to_add
    return(df)

if __name__ == "__main__":
    scraper = DFS_Scraper()
    
    
    #####
    # Scrape the players and salary data from FantasyPros - only need to do once
    #####

    scraper.navigate('salaries')
    qbs = scraper.get_player_salary('QB')
    rbs = scraper.get_player_salary('RB')
    wrs = scraper.get_player_salary('WR')
    tes = scraper.get_player_salary('TE')
    dsts = scraper.get_player_salary('DST')
    # Format the scraped player and salary data for joining later
    qb_salaries = scraper.format_salary_data(qbs)
    rb_salaries = scraper.format_salary_data(rbs)
    wr_salaries = scraper.format_salary_data(wrs)
    te_salaries = scraper.format_salary_data(tes)
    dst_salaries = scraper.format_salary_data(dsts)    
    
    
    #####
    # Scrape prop data from DraftKings
    #####
    
    scraper.navigate('props')
    td_odds = scraper.get_player_props('TD Scorers')
    scraper.navigate('props')
    passing_info = scraper.get_player_props('Passing Props')
    scraper.navigate('props')
    try: # Need to account for both different labels
        rush_rec_info = scraper.get_player_props('Rushing/Receiving Props')
    except:
        rush_rec_info = scraper.get_player_props('Rush/Rec Props')
    
    # combine scraped props into a projected DFS score
    expected_props_points = scraper.combine_props(td_odds, passing_info, rush_rec_info)
    
    
    #####
    # Scrape fantasy projections from ESPN
    #####
    scraper.navigate('fantasy')
    qb_projections = scraper.get_fantasy_projections('QB')
    rb_projections = scraper.get_fantasy_projections('RB')
    wr_projections = scraper.get_fantasy_projections('WR')
    te_projections = scraper.get_fantasy_projections('TE')
    def_projections = scraper.get_fantasy_projections('D/ST')
    
    
    #####
    # Combine data
    #####
    qb_data = scraper.combine_data(qb_salaries, expected_props_points, qb_projections)
    rb_data = scraper.combine_data(rb_salaries, expected_props_points, rb_projections)
    wr_data = scraper.combine_data(wr_salaries, expected_props_points, wr_projections)
    te_data = scraper.combine_data(te_salaries, expected_props_points, te_projections)
    #dst_data = scraper.combine_data(dst_salaries, None, def_projections) won't work how I currently have set up - need to be able to get a list of games
    scraper.quit()

    qb_data.to_csv(f'Output/qb_data_{dt.now().date()}.csv')
    rb_data.to_csv(f'Output/rb_data_{dt.now().date()}.csv')
    wr_data.to_csv(f'Output/wr_data_{dt.now().date()}.csv')
    te_data.to_csv(f'Output/te_data_{dt.now().date()}.csv')
    
