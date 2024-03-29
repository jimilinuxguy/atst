import stickybits from 'stickybits'

import checkboxinput from '../checkbox_input'
import ClinFields from '../clin_fields'
import DateSelector from '../date_selector'
import FormMixin from '../../mixins/form'
import optionsinput from '../options_input'
import SemiCollapsibleText from '../semi_collapsible_text'
import textinput from '../text_input'
import uploadinput from '../upload_input'

export default {
  name: 'to-form',

  mixins: [FormMixin],

  components: {
    checkboxinput,
    ClinFields,
    DateSelector,
    optionsinput,
    SemiCollapsibleText,
    textinput,
    uploadinput,
  },

  props: {
    initialClinCount: {
      type: Number,
      default: null,
    },
  },

  data: function() {
    const clins = !this.initialClinCount ? 1 : 0
    const clinIndex = !this.initialClinCount ? 0 : this.initialClinCount - 1

    return {
      clins,
      clinIndex,
    }
  },

  mounted: function() {
    this.$root.$on('remove-clin', this.handleRemoveClin)
  },

  methods: {
    addClin: function(event) {
      ++this.clins
      ++this.clinIndex
    },

    handleRemoveClin: function(event) {
      --this.clinIndex
      for (var field in this.fields) {
        if (field.includes('-' + event.clinIndex + '-')) {
          delete this.fields[field]
        }
      }

      this.validateForm()
    },
  },

  directives: {
    sticky: {
      inserted: (el, binding) => {
        var customAttributes
        if (binding.expression) {
          customAttributes = JSON.parse(binding.expression)
        }
        stickybits(el, customAttributes)
      },
    },
  },
}
