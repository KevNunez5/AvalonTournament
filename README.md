# AvalOnWeb

Sorry, the name is just a bad joke! Let's look for a better one!

Anyway, we have a first version of the Web-based Avalon workbench. The bots depend, all of them, in the first version of Dave's game logic.

The code is organized into two parts: A React-based frontend and a Websocket-based backend that runs the game logic (controller/moderator and bots).

The code requires Node.js and Python 3. Locally, I am using Node version 23.11 and Python 3.13.2. I would expect the code to run in older versions.

Now, let us install all the dependencies. In a terminal window, run the following commands:

```
cd backend
pip install -r requirements
```

The above install of the python libraries required to run the backend. To that end run `python3 main.py`to launch the web server. You will need to open another terminal window and change again to "backend" as the working directory. There, execute the command `python3 observer.py`. Open a third terminal window and go to the "backend" directory. Run there the command `python3 bots.py`. The latter launches 4 bots that start playing an instance of Avalon

Now, in another terminal window (yes, a forth one) and run the following commands:

```
cd frontend
npm install
npm run dev
```

This will download all javascript dependencies and start the frontend application. Open in a browser the  URL `http://localhost:5173`and you will see the web page of Avalon workbench. Click on the button "Join", then try to follow the game. You will have the opportunity of voting on the proposed teams and on the outcome of a quest using a form. Note that in this moment, the good ones are given the opportunity to vote against winning a quest but, please do not do it. It is just that the game is still incomplete. When you are asked to propose a team just write the list of team identifiers, using the javascript syntax (e.g. [0,1]), because nothing is validated yet. The system will generate a message for announcing your team.

If you want to run another instance of Avalon, you will need to stop the web server with Ctrl-C, and restart the three programs in the same order: 1) web server, 2) observer, 3) bots. Then, please reload the web page and click on the button "Join".
 