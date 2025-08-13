import { useRef, useState } from 'react'
import WebSocketAsPromised from 'websocket-as-promised';

import {defaultDarkModeOverride, Button, Card, Flex, Grid, Input, Text, TextAreaField, ThemeProvider} from '@aws-amplify/ui-react';
import "@chatscope/chat-ui-kit-styles/dist/default/styles.min.css";
import "./components/mystyles.css"
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput
} from "@chatscope/chat-ui-kit-react";

import MyMessage from "./components/MyMessage";
import MyVotingForm from './components/MyVotingForm';

function App() {
  const [role, setRole] = useState("");
  const [vote, setVote] = useState(null);

  const [messages, setMessages] = useState([]);
  let wspRef = useRef(null);
  let msgRef = useRef([]);
  let gameState = useRef({});

  const theme = {
    name: 'my-theme',
    overrides: [defaultDarkModeOverride],
  };

  let wrapperSetVote = (value) => {
    console.log("changed to", value);
    setVote(value);
  }
  let createNewGame = () => {
    console.log("... createNewGame");
    fetch("http://localhost:8888/games", {
      method: "POST"
    }).then(resp => {
      console.log("Reached the right point ...");
      const wsp = new WebSocketAsPromised('ws://localhost:8888/ws');
      wsp.open().then(() => {
        wspRef.current = wsp;
        wsp.onMessage.addListener(data => {
          var msg = JSON.parse(data);
          console.log(data);
          // setRole(msg.message)
          msgRef.current.push(msg.message);
          console.log(messages, msgRef.current);
          setMessages([...messages, (<MyMessage message={msg.message} playerId="2"/>)])
          console.log(messages);
        });
        console.log("received:", resp);
      });
    });
  };

  let joinGame = () => {
    console.log("... joinGame");
    const wsp = new WebSocketAsPromised('ws://localhost:8888/ws');
    wsp.open().then(() => {
      wspRef.current = wsp;
      wsp.onMessage.addListener(data => {
        var msg = JSON.parse(data);
        if (msg["action"] && msg["action"] == "RevealRoles") {
          console.log("Reveal ... roles");
          gameState.current = {
            index: msg["index"],
            role: msg["roles"][msg["index"]],
            stage: "RevealingRoles"
          };
          setRole(gameState.current.role);
          console.log("Your game info:", gameState.current);
          msgRef.current.push({"msg": `I am Player ${gameState.current.index}, with role '${gameState.current.role}'`, "index": -1});
          return;
        } else if (msg["action"] && msg["action"] == "VoteTeam") {
          gameState.current.stage = "VotingTeam";
          setVote(null);
        } else if (msg["action"] && msg["action"] == "VoteQuest") {
          gameState.current.stage = "VotingQuest";
          setVote(null);
        } else if (msg["action"] && msg["action"] == "SelectTeam") {
          gameState.current.stage = "SelectingTeam";
        } else {
          console.log("cont ...")
        }
        console.log(data);
        // setRole(msg.message)
        msgRef.current.push(msg);
        console.log(messages, msgRef.current);
        setMessages([...messages, (<MyMessage message={msg.message} playerId={msg.index}/>)])
        console.log(messages);
      });
      console.log("received:", resp);
    });
  };

  let sendMessage = (message) => {
    console.log(message);
    if (wspRef.current) {
      console.log(wspRef)
      var payload = {
        index: gameState.current.index,
        message: message
      };
      if (gameState.current.stage == "VotingTeam") {
        payload.vote = vote == "yes";
        payload.event = "TeamVoted";
        gameState.current.stage = "TeamVoted";
      } else if (gameState.current.stage == "VotingQuest") {
        payload.vote = vote == "yes";
        payload.event = "QuestVoted";
        gameState.current.stage = "QuestVoted";
      } else if (gameState.current.stage == "SelectingTeam") {
        payload.team = JSON.parse(message);
        payload.message = `Player ${payload.index} selected team ${message}`;
        payload.event = "TeamSelected";
      }
      wspRef.current.send(JSON.stringify(payload));
    }
  };

  var castVote = () => sendMessage(`Player ${gameState.current.index} voted` + (gameState.current.stage == "VotingTeam" ? ` '${vote}' on team` : ""));

  var votingFormIfNeeded = () => {
    if (gameState.current.stage == "VotingTeam") {
      return (
          <MyVotingForm legend="Vote on the proposed team"
            negativeEnabled={role == "evil"}
            vote={vote} 
            setVote={wrapperSetVote}
            onSubmit={castVote}
            />
      );
    } else if (gameState.current.stage == "VotingQuest") {
      return (
        <MyVotingForm legend="Vote on quest outcome"
          negativeEnabled={role == "evil"}
          vote={vote} 
          setVote={wrapperSetVote}
          onSubmit={castVote}
          />
      );
    }
    return null;
  };

  return (
      <ThemeProvider theme={theme} colorMode='dark'>
      <Grid
        templateColumns="1fr 1fr 1fr 1fr"
        templateRows="1fr 1fr 8fr"
      >

      <Card columnStart="1" columnEnd="3">
        <Button onClick={createNewGame}>
          New game
        </Button>
      </Card>
      <Card columnStart="3" columnEnd="-1">
        <Flex direction="row" gap="small">
        <Input placeholder='Game Id'></Input>
        <Button onClick={joinGame}>
          Join
        </Button>
        </Flex>
      </Card>
      <Card columnStart="1" columnEnd="3" rowStart="2" rowEnd="-1">
        abc
      </Card>
      <Card columnStart="3" columnEnd="-1" rowStart="2" rowEnd="3">
      <Text>Role: {role}</Text>
      </Card>
      <Card columnStart="3" columnEnd="-1" rowStart="3" rowEnd="-1">
        <div style={{ position: "relative", height: "550px" }}>

  <MainContainer>
    <ChatContainer>
      <MessageList>
        {msgRef.current.map(msg => (<MyMessage message={msg.message} playerId={msg.index} isNarrator={msg.index == -1} />))}
        {votingFormIfNeeded()}
      </MessageList>
      <MessageInput placeholder="Type message here" onSend={sendMessage} />
    </ChatContainer>
  </MainContainer>
</div>
      </Card>
      </Grid>
      </ThemeProvider>
  )
}

export default App
