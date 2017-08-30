import React from 'react';
import Textarea from 'react-textarea-autosize';
import PropTypes from 'prop-types'

export default class EditableNotes extends React.Component {
  constructor(props) {
    super(props);
    this.saveNotes = this.saveNotes.bind(this);
    this.handleChange = this.handleChange.bind(this);
    this.keyPress = this.keyPress.bind(this);
    this.state = {
      value: this.props.value
    }
  }

  // Simulate a click on the field to enter editing state upon mount
  //    Have to target child through parent b/c TextArea cannot be directly referenced
  componentDidMount() {
    if (this.props.startFocused)
      this.textInput.childNodes[0].focus();
  }

  // Make Enter key save the text in edit field, overriding default newline
  keyPress(e) {
    if (e.key == 'Enter' ) {
      e.preventDefault();
      this.saveNotes();
    }
  }

  // If nothing entered, saves a default note and closes
  saveNotes() {
    let value = this.state.value;

    if (!value || (value == "") || (value == "Write notes here")) {
      this.props.api.setWfModuleNotes(this.props.wfModuleId, "Write notes here");
      this.props.hideNotes();
    } else {
      this.props.api.setWfModuleNotes(this.props.wfModuleId, value);
    }

    // call blur on self to stop blinky cursor
    // Have to target child through parent b/c TextArea cannot be directly referenced
    this.textInput.childNodes[0].blur();
  }

  handleChange(event) {
    this.setState({value: event.target.value});
  }

  render() {

    return <div
              ref={ (input) => { this.textInput = input; } }
              className=''
            >
            {this.props.isReadOnly 
              ? ( <span className='content-3 t-d-gray'>{this.props.value}</span> )
              : ( 
                  <Textarea
                    value={this.state.value}
                    onChange={this.handleChange}
                    onBlur={this.saveNotes}
                    onKeyPress={this.keyPress}
                    className='editable-notes-field'
                  >
                  </Textarea>
                )
            }
          </div>
  }
}

EditableNotes.propTypes = {
  value:          PropTypes.string,
  wfModuleId:     PropTypes.number.isRequired,
  hideNotes:      PropTypes.func.isRequired,
  api:            PropTypes.object.isRequired,
  isReadOnly:     PropTypes.bool.isRequired,
  hideNotes:      PropTypes.func.isRequired,
  startFocused:   PropTypes.bool.isRequired,
};

