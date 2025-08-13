import {Flex} from '@aws-amplify/ui-react';
import {Message} from "@chatscope/chat-ui-kit-react";
import "./mystyles.css";

function MyMessage(props) {
    if (!("isNarrator" in props))
      props.isNarrator = false;
    return (
        <>
        <Flex dir='row'>
        {props.playerId >= 0 ? (
        <svg width={36} height={40}>
          <image x="0" y="7" width="30" href="/hoplite_2155545.png"/>
          <circle cx="26" cy="26" r="10" fill="#cc0000"/>
          <text x="21" y="31" fontFamily="Arial, Helvetica, sans-serif" fontWeight="bold" fontSize="16" fill="white"> {props.playerId}</text>
        </svg>) : null }
        <Message
          model={{
            message: props.message,
            sentTime: "just now",
            sender: "Joe",
            direction: (props.isNarrator ? "outgoing" : "incoming")
          }}
        />
        </Flex>
        </>
    );
}

export default MyMessage;