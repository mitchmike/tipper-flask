# TIPPER


#### Video Demo: https://youtu.be/ru34YU4Ub48

#### Description:
This is my final project for CS50 called Tipper.
It is a website that provides insights into AFL (Australian Rules Football) and informs users on odds and likelihoods that a team will win a given match. For now it is a prototype, but eventually it will be using machine learning algorithms to predict winners and find valuable bets based on market odds.

It runs on a flask web server and utilises a NodeJS API that is connected to a postgresQL database containing football statistics. The API was an exising project and my final project involved creating the flask app and adding a few new endpoints to the node API.


The Main Pages available are as follows

####Tip:
This page shows a list of upcoming games where there are market odds available
Upon clicking on a game, the page populates details of the game including:
- a Tipper score (currently a random number but eventually will be a Machine Learning generated score)
- The odds from various betting providers (sourced from the odds API on a free trial for the prototype)
#####Design Choices:
- This page uses a lot of dynamic injection using jinja - for games, team logos, links, and table data
- The page uses bootstrap to make a nice clean responsive design
- i chose to use the odds api as this gives an easy and simple json response from various betting companies and is much easier to implement than scraping various websites for data


####Ladder:
This page shows the current ladder positions of all teams. It is using data from a postgresQL database (via the node API that i have written). This game data was initially scraped from the official AFL statistics website.
Each row is a link to the detail page for that team and is highlighted with the official team logo colour (exact rgb taken from their logos). The ladder for previous seasons can also be selected and viewed
#####Design choices:
- The page is fairly simple, using bootstrap for a clean responsive design
- The colours on each row make the site feel more interactive and interesting for the user


####Team Detail:
This page can be accessed from various other links on the site including from Ladder and Tip. The page gives extra details on the team. For the prototype, the page simply displays recent games played with colour coding for win/loss, as well as a graph that displays data that i have computed from the DB data via the node API. The computation takes the totals for a team and their opponent for a given statistic (eg kicks) in a given round, and calculates a percentage difference between the teams. e.g. if richmond had 20% more kicks than their round 1 opponent then the graph would show 20% (or 0.2) for round 1 for richmond for the kicks series. This stat can give an indication of how a team performs in comparison to their component in a given aspect of the game.
#####Design choices:
- The chart is using CanvasJS on a free trial. 
- I am dynamically enterring the data via a jinja template so users can select different statistics that they would like to display via the checkboxes. 
- When clicking 'Display Stats' the page will reload at the same scroll position, and all the stats that are displaying on the chart will have their checkbox still selected.
- The data and logos are all dynamically filled into jinja templates

