# flake8: noqa
from django import forms
from django.utils.translation import get_language_bidi
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils.encoding import force_text
from django.forms.fields import Field, ChoiceField
from itertools import groupby, chain

try:
    from django.forms.utils import flatatt
except:
    # for django 1.6
    from django.forms.util import flatatt


class ModelChoiceIterator_bool(forms.models.ModelChoiceIterator):
    def __init__(self, field, bool_field, group_by_field):
        self.bool_field = bool_field
        self.field = field
        self.queryset = field.queryset
        self.group_by_field = group_by_field

    def __iter__(self):
        if self.field.empty_label is not None:
            yield (u"", self.field.empty_label)
        items = self.queryset.all()
        if self.group_by_field:
            items = items.order_by(self.group_by_field)
        if self.field.cache_choices:
            if self.field.choice_cache is None:
                if self.group_by_field:
                    self.field.choice_cache = [(self.field.group_label(group), [self.choice(ch) for ch in choices])
                                               for group, choices in groupby(items, key=lambda row: getattr(row, self.group_by_field))]
                else:
                    self.field.choice_cache = [self.choice(obj) for obj in items]
            for choice in self.field.choice_cache:
                yield choice
        else:
            if self.group_by_field:
                for group, choices in groupby(items, key=lambda row: getattr(row, self.group_by_field)):
                    yield (self.field.group_label(group), [self.choice(ch) for ch in choices])
            else:
                for obj in items:
                    yield self.choice(obj)

    def choice(self, obj):
        value = getattr(obj, self.bool_field, True) if self.bool_field else None
        return (self.field.prepare_value(obj), self.field.label_from_instance(obj), value)


class ModelChoiceField_bool(forms.ModelChoiceField):
    def __init__(self, queryset, empty_label="---------", cache_choices=False,
                 required=True, widget=None, label=None, initial=None,
                 help_text='', to_field_name=None, *args, **kwargs):
        if required and (initial is not None):
            self.empty_label = None
        else:
            self.empty_label = empty_label
        self.cache_choices = cache_choices
        Field.__init__(self, required, widget, label, initial, help_text,
                       *args, **kwargs)
        self.queryset = queryset
        self.choice_cache = None
        self.to_field_name = to_field_name

    def _get_choices(self):
        if hasattr(self, '_choices'):
            return self._choices
        return ModelChoiceIterator_bool(self, self.bool_field, self.group_by_field)

    choices = property(_get_choices, ChoiceField._set_choices)


class ChosenWidgetMixin(object):

    class Media:
        css = {'all': ('/static/chosen/css/chosen.css',)}
        js = ('/static/chosen/js/chosen.jquery_1.6.js',
              '/static/chosen/js/chosen.jquery_ready.js')

    js = '''<script type="text/javascript">for (var selector in chosen_config) {$(selector).chosen(chosen_config[selector]);}</script>'''

    def __init__(self, attrs={}, *args, **kwargs):

        attrs['data-placeholder'] = kwargs.pop('overlay', None)
        attrs['class'] = "class" in attrs and self.add_to_css_class(attrs['class'], 'chosen-select') or "chosen-select"
        if get_language_bidi():
            attrs['class'] = self.add_to_css_class(attrs['class'], 'chosen-rtl')
        super(ChosenWidgetMixin, self).__init__(attrs, *args, **kwargs)

    def render(self, name, value, attrs=None, choices=()):
        if not self.is_required:
            self.attrs.update({'data-optional': True})
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        output = [format_html(u'<select{0}>', flatatt(final_attrs))]
        options = self.render_options(choices, [value])
        if options:
            output.append(options)
        output.append('</select>')
        return mark_safe('\n'.join(output))

    def render_option(self, selected_choices, option_value, option_label, bool_field):
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        disabled = 'disabled' if bool_field else ''
        return format_html(u'<option {0} value="{1}"{2}>{3}</option>',
                           disabled,
                           option_value,
                           selected_html,
                           force_text(option_label))

    def render_options(self, choices, selected_choices):
        selected_choices = set(force_text(v) for v in selected_choices)
        output = []
        self.choices = [d for d in self.choices]
        self.choices[0] += (False,)
        for option in chain(self.choices, choices):
            if len(option) == 2:
                (option_value, option_label) = option
            else:
                (option_value, option_label, bool_field) = option
            if isinstance(option_label, (list, tuple)):
                output.append(format_html(u'<optgroup label="{0}">', force_text(option_value)))
                for option in option_label:
                    output.append(self.render_option(selected_choices, *option))
                output.append('</optgroup>')
            else:
                output.append(self.render_option(selected_choices, option_value, option_label, bool_field))
        return '\n'.join(output)

    def add_to_css_class(self, classes, new_class):
        new_classes = classes
        try:
            classes_test = u" " + unicode(classes) + u" "
            new_class_test = u" " + unicode(new_class) + u" "
            if new_class_test not in classes_test:
                new_classes += u" " + unicode(new_class)
        except TypeError:
            pass
        return new_classes


class ChosenSelect(ChosenWidgetMixin, forms.Select):
    pass


class ChosenSelectMultiple(ChosenWidgetMixin, forms.SelectMultiple):
    pass


class ChosenGroupSelect(ChosenSelect):

    def __init__(self, attrs={}, *args, **kwargs):
        super(ChosenGroupSelect, self).__init__(attrs, *args, **kwargs)
        attrs["class"] = "chosen-single chosen-with-drop"


class ChosenFieldMixin(object):

    def __init__(self, *args, **kwargs):
        widget_kwargs = "overlay" in kwargs and {"overlay": kwargs.pop('overlay')} or {}
        kwargs['widget'] = self.widget(**widget_kwargs)
        super(ChosenFieldMixin, self).__init__(*args, **kwargs)


class ChosenChoiceField(ChosenFieldMixin, forms.ChoiceField):

    widget = ChosenSelect


class ChosenMultipleChoiceField(ChosenFieldMixin, forms.MultipleChoiceField):

    widget = ChosenSelectMultiple


class ChosenModelChoiceField(ChosenFieldMixin, ModelChoiceField_bool):
    def __init__(self, bool_field=None, group_by_field=None, group_label=None, *args, **kwargs):
        self.query = kwargs.get('queryset')
        self.bool_field = bool_field
        self.group_by_field = group_by_field
        if group_label is None:
            self.group_label = lambda group: group
        else:
            self.group_label = group_label
        super(ChosenModelChoiceField, self).__init__(*args, **kwargs)

    widget = ChosenSelect


class ChosenModelMultipleChoiceField(ChosenFieldMixin, forms.ModelMultipleChoiceField):

    widget = ChosenSelectMultiple


class ChosenGroupChoiceField(ChosenFieldMixin, forms.ChoiceField):

    widget = ChosenGroupSelect
