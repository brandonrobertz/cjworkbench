import React from 'react'
import PropTypes from 'prop-types'
import WfHamburgerMenu from './WfHamburgerMenu'
import UndoRedoButtons from './UndoRedoButtons'
import ConnectedEditableWorkflowName, { EditableWorkflowName } from './EditableWorkflowName'
import { goToUrl, timeDifference } from './utils'
import ShareButton from './ShareModal/ShareButton'
import { Trans } from '@lingui/macro'

function NoOp () {}

function LessonCourse ({ course }) {
  let path
  let title

  if (course) {
    path = '/courses/' + course.slug
    title = course.title
  } else {
    path = '/lessons'
    title = 'Training'
  }

  return (
    <div className='course'>
      <a href={path}>{title}</a>
    </div>
  )
}

function LessonWorkflowTitle ({ lesson }) {
  return (
    <div className='title-metadata-stack'>
      <LessonCourse course={lesson.course} />
      <EditableWorkflowName
        value={lesson.header.title}
        setWorkflowName={NoOp}
        isReadOnly
      />
    </div>
  )
}

function OwnedWorkflowTitleAndMetadata ({ isReadOnly, workflow }) {
  return (
    <div className='title-metadata-stack'>
      <ConnectedEditableWorkflowName isReadOnly={isReadOnly} />
      <ul className='metadata-container'>
        {!workflow.is_anonymous ? (
          <li className='attribution'>
            <span className='metadata'>by {workflow.owner_name.trim()}</span>
            <span className='separator'>-</span>
          </li>
        ) : null}
        <li>
          Updated {timeDifference(workflow.last_update, new Date())}
        </li>
        {(!isReadOnly && !workflow.is_anonymous) ? (
          <li>
            <span className='separator'>-</span>
            <ShareButton>
              {workflow.public ? <Trans>public</Trans> : <Trans>private</Trans>}
            </ShareButton>
          </li>
        ) : null}
      </ul>
    </div>
  )
}

function WorkflowTitleAndMetadata ({ lesson, isReadOnly, workflow }) {
  if (lesson) {
    return (
      <LessonWorkflowTitle
        lesson={lesson}
      />
    )
  } else {
    return (
      <OwnedWorkflowTitleAndMetadata
        isReadOnly={isReadOnly}
        workflow={workflow}
      />
    )
  }
}

export default class WorkflowNavBar extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    workflow: PropTypes.object.isRequired,
    lesson: PropTypes.shape({
      course: PropTypes.shape({
        slug: PropTypes.string.isRequired,
        title: PropTypes.string.isRequired
      }), // optional -- no course means plain lesson
      header: PropTypes.shape({
        title: PropTypes.string.isRequired
      }).isRequired
    }), // optional -- no lesson means we're not in the "lessons" interface
    isReadOnly: PropTypes.bool.isRequired,
    loggedInUser: PropTypes.object // undefined if no user logged in
  }

  state = {
    spinnerVisible: false,
    isShareModalOpen: false
  }

  componentWillUnmount = () => {
    this.unmounted = true
  }

  undoRedo (verb) {
    // TODO use reducer for this, with a global "can't tell what's going to
    // change" flag instead of this.state.spinnerVisible.

    // Prevent keyboard shortcuts or mouse double-undoing.
    if (this.state.spinnerVisible) return

    this.setState({ spinnerVisible: true })
    this.props.api[verb](this.props.workflow.id)
      .then(() => {
        if (this.unmounted) return
        this.setState({ spinnerVisible: false })
      })
  }

  undo = () => {
    this.undoRedo('undo')
  }

  redo = () => {
    this.undoRedo('redo')
  }

  handleDuplicate = () => {
    if (!this.props.loggedInUser) {
      // user is NOT logged in, so navigate to sign in
      goToUrl('/account/login')
    } else {
      // user IS logged in: start spinner, make duplicate & navigate there
      this.setState({ spinnerVisible: true })

      this.props.api.duplicateWorkflow(this.props.workflow.id)
        .then(json => {
          goToUrl('/workflows/' + json.id)
        })
    }
  }

  render () {
    const { api, isReadOnly, loggedInUser, lesson, workflow } = this.props

    // menu only if there is a logged-in user
    let contextMenu
    if (loggedInUser) {
      contextMenu = (
        <WfHamburgerMenu
          workflowId={workflow.id}
          api={api}
          isReadOnly={isReadOnly}
          user={loggedInUser}
        />
      )
    } else {
      contextMenu = (
        <a href='/account/login' className='nav--link'>Sign in</a>
      )
    }

    const spinner = this.state.spinnerVisible ? (
      <div className='spinner-container'>
        <div className='spinner-l1'>
          <div className='spinner-l2'>
            <div className='spinner-l3' />
          </div>
        </div>
      </div>
    ) : null

    return (
      <React.Fragment>
        {spinner}
        <nav className='navbar'>
          <div className='navbar-elements'>
            <a href='/workflows/' className='logo-navbar'>
              <img className='image' src={`${window.STATIC_URL}images/logo.svg`} />
            </a>
            <WorkflowTitleAndMetadata
              lesson={lesson}
              isReadOnly={isReadOnly}
              workflow={workflow}
            />
            <div className='nav-buttons'>
              {isReadOnly ? null : (
                <UndoRedoButtons undo={this.undo} redo={this.redo} />
              )}
              <button name='duplicate' onClick={this.handleDuplicate}>Duplicate</button>
              {lesson ? null : (/* We haven't yet designed what it means to share a lesson workflow. */
                <ShareButton>Share</ShareButton>
              )}
              {contextMenu}
            </div>
          </div>
        </nav>
      </React.Fragment>
    )
  }
}
