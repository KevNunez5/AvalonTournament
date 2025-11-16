import { Button, Radio, RadioGroupField } from "@aws-amplify/ui-react";

function MyVotingForm(props) {
  return (
    <RadioGroupField style={{backgroundColor: 'white', color: 'white', height: '42px', paddingLeft: '8px', padding: '4px', marginTop: '4px'}} 
        legend={props.legend} 
        value={props.vote}
        onChange={(e) => props.setVote(e.target.value)}
        direction="row">
      <Radio value={"yes"}>For</Radio>
      <Radio value={"no"}>Against</Radio>
      <Button isDisabled={props.vote == null} onClick={props.onSubmit} variation="primary" size="small" style={{marginLeft: "10px"}}>Submit</Button>
    </RadioGroupField>
  )};

export default MyVotingForm;
