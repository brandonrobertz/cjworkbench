// UI for a single module within a workflow

import React, { PropTypes } from 'react'
import WfParameter from './WfParameter'
import TableView from './TableView'
import { store, wfModuleStatusAction } from './workflow-reducer'
import { csrfToken } from './utils'
import * as Actions from './workflow-reducer'

// Libraries to provide a collapsable table view
import { Collapse, Button, CardBlock, Card } from 'reactstrap';


// ---- StatusLight ----
// Ready, Busy, or Error
class StatusLight extends React.Component {
  render() {
    return <div className={this.props.status + '-light'}></div>
  }
}

// ---- StatusLine ----
// Display error message, if any
class StatusLine extends React.Component {
  render() {
    if (this.props.status == 'error') {
      return <div className='wfModuleErrorMsg'>{this.props.error_msg}</div>
    } else if (this.props.status == 'busy') {
      return <div className='wfModuleErrorMsg'>Working...</div>
    } else {
      return false
    }
  }
}

// ---- WfModule ----


export default class WfModule extends React.Component {

  constructor(props) {
    super(props);
    this.initFields(props);
    this.click = this.click.bind(this);
    this.setParamText = this.setParamText.bind(this);
    this.getParamText = this.getParamText.bind(this);
    this.removeModule = this.removeModule.bind(this);
  }

  // our props are annoying (we use data- because Sortable puts all these props om the DOM object)
  // so save them into this
  initFields(props) {
    this.wf_module = props['data-wfmodule'];
    this.module = this.wf_module.module;
    this.params = this.wf_module.parameter_vals;
    this.revision = props['data-revision'];
  }

  // alas, the drawback of the convienence of initFields is we need to call it whenever props change
  componentWillReceiveProps(newProps) {
    this.initFields(newProps)
  }

  // We become the selected module on any click
  click(e) {
    Actions.store.dispatch(Actions.changeSelectedWfModuleAction(this.wf_module.id));
  }

  // These functions allow parameters to access each others value (text params only)
  // Used e.g. for custom UI elements to save/restore their state from hidden parameters
  // Suppresses reassignment of the same text, which can be important to avoid endless notification loops
  setParamText(id_name, text) {
    var p = this.params.find( p => p.parameter_spec.id_name == id_name );
    if (p && text != p.string) {
      this.props['data-changeParam'](p.id, { value: text })
    }
  }

  getParamText(id_name) {
    //console.log("getParamText " + id_name)
    var p = this.params.find( p => p.parameter_spec.id_name == id_name );
    if (p) {
      return p.value;
    }
  }

  removeModule(e) {
    this.props['data-removeModule'](this.wf_module.id);
    e.stopPropagation();  // necessary, or we will select the module we just deleted => bad
  }

  render() {

    // Each parameter gets a WfParameter
    var paramdivs = this.params.map((ps, i) => {
        return <WfParameter
          key={i}
          p={ps}
          changeParam={this.props['data-changeParam']}
          wf_module_id={this.wf_module.id}
          revision={this.revision}
          getParamText={this.getParamText}
          setParamText={this.setParamText} />
      });

    // var cardClass = this.props['data-selected'] ?
    //   'card w-75 mx-auto mb-4 bg-selected-module':
    //   'card w-75 mx-auto mb-4 bg-faded';

    // as above, but removing margins
    var cardClass = this.props['data-selected'] ?
      'card w-75 mx-auto bg-selected-module':
      'card w-75 mx-auto bg-faded';

    // Putting it all together: name, status, parameters, output
    return (
      <div className='container' {...this.props} onClick={this.click}>
        <div className={cardClass}>
          <div className='card-block p-1'>

            <div className='d-flex justify-content-between align-items-center mb-2'>
                <button type='button' className='btn btn-secondary btn-sm' onClick={this.removeModule}>&times;</button>
                <h4 className='text-center mb-0'>{this.module.name}</h4>
                <StatusLight status={this.wf_module.status}/>
            </div>
            <StatusLine status={this.wf_module.status} error_msg={this.wf_module.error_msg} />
            {paramdivs}
            <a className='ml-2' href={'/public/moduledata/live/' + this.wf_module.id + '.csv'}>CSV</a>/<a href={'/public/moduledata/live/' + this.wf_module.id + '.json'}>JSON</a>
          </div>

        </div>
      </div>
    ); 
  } 
}


WfModule.propTypes = {
  'data-wfmodule':      React.PropTypes.object,
  'data-revison':       React.PropTypes.number,
  'data-selected':      React.PropTypes.bool,
  'data-changeParam':   React.PropTypes.func,
  'data-removeModule':  React.PropTypes.func
};
