from functools import partial
import logging
import maya.cmds as cmds
from cmt.qt import QtWidgets
import cmt.cqueue.core as core
import cmt.cqueue.fields as fields
logger = logging.getLogger(__name__)


class ParentConstraintView(fields.ContainerView):
    """Customize the view of the container."""
    def widget(self, container):
        widget = QtWidgets.QFrame()
        widget.setFrameStyle(QtWidgets.QFrame.StyledPanel)

        hbox = QtWidgets.QHBoxLayout(widget)
        hbox.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel(container['drivers'].verbose_name)
        hbox.addWidget(label)
        drivers_widget = container['drivers'].widget()
        drivers_widget.setMaximumHeight(65)
        hbox.addWidget(drivers_widget)

        vbox = QtWidgets.QVBoxLayout()
        hbox.addLayout(vbox)

        hbox1 = QtWidgets.QHBoxLayout()
        vbox.addLayout(hbox1)
        label = QtWidgets.QLabel(container['driven'].verbose_name)
        hbox1.addWidget(label)
        hbox1.addWidget(container['driven'].widget())
        hbox1.addWidget(container['maintain_offset'].widget())

        hbox2 = QtWidgets.QHBoxLayout()
        vbox.addLayout(hbox2)
        hbox2.setContentsMargins(0, 0, 0, 0)
        hbox2.addWidget(container['skip_tx'].widget())
        hbox2.addWidget(container['skip_ty'].widget())
        hbox2.addWidget(container['skip_tz'].widget())
        hbox2.addStretch()

        hbox3 = QtWidgets.QHBoxLayout()
        vbox.addLayout(hbox3)
        hbox3.setContentsMargins(0, 0, 0, 0)
        hbox3.addWidget(container['skip_rx'].widget())
        hbox3.addWidget(container['skip_ry'].widget())
        hbox3.addWidget(container['skip_rz'].widget())
        hbox3.addStretch()

        return widget


class Component(core.Component):
    """A Component that creates parentConstraints."""
    constraints = fields.ArrayField('constraints', add_label_text='Add Parent Constraint')
    container = fields.ContainerField('constraint', parent=constraints, container_view=ParentConstraintView())
    drivers = fields.MayaNodeField('drivers', multi=True, help_text='The nodes to constrain to.', parent=container)
    driven = fields.MayaNodeField('driven', help_text='The node to constrain.', parent=container)
    maintain_offset = fields.BooleanField('maintain_offset', default=True, parent=container)
    skip_tx = fields.BooleanField('skip_tx', verbose_name='Skip tx', parent=container)
    skip_ty = fields.BooleanField('skip_ty', verbose_name='Skip ty', parent=container)
    skip_tz = fields.BooleanField('skip_tz', verbose_name='Skip tz', parent=container)
    skip_rx = fields.BooleanField('skip_rx', verbose_name='Skip rx', parent=container)
    skip_ry = fields.BooleanField('skip_ry', verbose_name='Skip ry', parent=container)
    skip_rz = fields.BooleanField('skip_rz', verbose_name='Skip rz', parent=container)

    @classmethod
    def image_path(cls):
        return ':/parentConstraint.png'

    def widget(self):
        """Override the widget to add a button to auto-populate fields from selected constraints.
        :return: The QWidget of the ArrayField.
        """
        widget = self.constraints.widget()
        # Add a new button to the widget button_layout to add selected constraints to the UI.
        button = QtWidgets.QPushButton('Add from Selected')
        button.released.connect(partial(self.add_from_selected, field_layout=widget.layout()))
        widget.button_layout.addWidget(button)
        return widget

    def add_from_selected(self, field_layout):
        # Get parentConstraints from the selected nodes
        sel = cmds.ls(sl=True) or []
        constraints = [x for x in sel if cmds.nodeType(x) == 'parentConstraint']
        transforms = [x for x in sel if cmds.nodeType(x) in ['transform', 'joint']]
        for transform in transforms:
            constraints += (cmds.listConnections(transform, type='parentConstraint') or [])
        constraints = list(set(constraints))
        for constraint in constraints:
            # Update the UI with the added constraint
            data = constraint_data(constraint)
            self.constraints.add_element(data=data, field_layout=field_layout)

    def execute(self):
        for container in self.constraints:
            drivers = container['drivers'].value()
            driven = container['driven'].value()
            skip_translate = [x for x in 'xyz' if container['skip_t{0}'.format(x)].value()]
            skip_rotate = [x for x in 'xyz' if container['skip_r{0}'.format(x)].value()]
            cmds.parentConstraint(drivers, driven,
                                  maintainOffset=container['maintain_offset'].value(),
                                  skipTranslate=skip_translate,
                                  skipRotate=skip_rotate)


def constraint_data(constraint):
    """Gets the parentConstraint data dictionary of the given constraint.

    The data dictionary can be used as input into the Component.
    :param constraint: Name of a parentConstraint node.
    :return: The parentConstraint data dictionary.
    """
    data = {
        'drivers': cmds.parentConstraint(constraint, q=True, targetList=True),
        'driven': cmds.listConnections('{0}.constraintParentInverseMatrix'.format(constraint), d=False)[0],
        'maintain_offset': False,
        'skip_tx': False,
        'skip_ty': False,
        'skip_tz': False,
        'skip_rx': False,
        'skip_ry': False,
        'skip_rz': False,
    }

    offset = cmds.getAttr('{0}.target[0].targetOffsetTranslate'.format(constraint))[0]
    offset += cmds.getAttr('{0}.target[0].targetOffsetRotate'.format(constraint))[0]
    for value in offset:
        if abs(value) > 0.000001:
            data['maintain_offset'] = True
            break
    for x in 'xyz':
        connection = cmds.listConnections('{0}.t{1}'.format(data['driven'], x), d=False)
        if not connection or connection[0] != constraint:
            data['skip_t{0}'.format(x)] = True

        connection = cmds.listConnections('{0}.r{1}'.format(data['driven'], x), d=False)
        if not connection or connection[0] != constraint:
            data['skip_r{0}'.format(x)] = True
    return data

