"""Helpers for :mod:`accounts.controllers`."""
from typing import Dict, Any

from wtforms.widgets import ListWidget, CheckboxInput, Select, \
    html_params
from wtforms import StringField, PasswordField, SelectField, \
    SelectMultipleField, Form
from markupsafe import Markup

class MultiCheckboxField(SelectMultipleField):
    """Multi-select with checkbox inputs."""

    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

    def __call__(self, ul_class: str = '', **kwargs: Any) -> str:
        """Render the multi-checkbox field."""
        kwargs.setdefault('type', 'checkbox')
        li_class = kwargs.pop('li_class')
        field_id = kwargs.pop('id', self.id)
        html = ['<ul %s>' % html_params(id=field_id, class_=ul_class)]
        for value, label, checked in self.iter_choices():
            choice_id = '%s-%s' % (field_id, value)
            options = dict(kwargs, name=self.name, value=value, id=choice_id)
            if checked:
                options['checked'] = 'checked'
            html.append(f'<li class="{li_class}">')
            html.append(f'<input {html_params(**options)} />')
            html.append(f'<label for="{choice_id}">{label}</label></li>')
            html.append('</li>')
        html.append('</ul>')
        return ''.join(html)


class OptGroupSelectWidget(Select):
    """Select widget with optgroups."""

    def __call__(self, field: SelectField, **kwargs: Any) -> Markup:
        """Render the `select` element with `optgroup`s."""
        kwargs.setdefault('id', field.id)
        if self.multiple:
            kwargs['multiple'] = True
        html = [f'<select {html_params(name=field.name, **kwargs)}>']
        html.append('<option></option>')
        for group_label, items in field.choices:
            html.append('<optgroup %s>' % html_params(label=group_label))
            for value, label in items:
                option = self.render_option(value, label, value == field.data)
                html.append(option)
            html.append('</optgroup>')
        html.append('</select>')
        return Markup(''.join(html))


class OptGroupSelectField(SelectField):
    """A select field with optgroups."""

    widget = OptGroupSelectWidget()

    def pre_validate(self, form: Form) -> None:
        """Don't forget to validate also values from embedded lists."""
        for group_label, items in self.choices:
            for value, label in items:
                if value == self.data:
                    return
        raise ValueError(self.gettext('Not a valid choice'))
