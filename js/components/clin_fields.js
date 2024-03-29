import { emitEvent } from '../lib/emitters'
import Modal from '../mixins/modal'
import optionsinput from './options_input'
import textinput from './text_input'
import clindollaramount from './clin_dollar_amount'
import PopDateRange from './pop_date_range'

const TOTAL_AMOUNT = 'total_amount'
const OBLIGATED_AMOUNT = 'obligated_amount'
const NUMBER = 'number'

export default {
  name: 'clin-fields',

  components: {
    optionsinput,
    textinput,
    clindollaramount,
    PopDateRange,
  },

  mixins: [Modal],

  props: {
    initialClinIndex: Number,
    initialTotal: {
      type: Number,
      default: 0,
    },
    initialObligated: {
      type: Number,
      default: 0,
    },
    initialClinNumber: {
      type: String,
      default: null,
    },
  },

  data: function() {
    const fundingValidation =
      this.initialObligated && this.initialTotal
        ? this.initialObligated <= this.initialTotal
        : true
    const clinNumber = !!this.initialClinNumber
      ? this.initialClinNumber
      : undefined

    return {
      clinIndex: this.initialClinIndex,
      clinNumber: clinNumber,
      clinNumber: clinNumber,
      showClin: true,
      totalAmount: this.initialTotal || 0,
      obligatedAmount: this.initialObligated || 0,
      fundingValid: fundingValidation,
    }
  },

  mounted: function() {
    this.$root.$on('field-change', this.handleFieldChange)
    this.validateFunding()
  },

  created: function() {
    emitEvent('clin-change', this, {
      id: this._uid,
      obligatedAmount: this.initialObligated,
      totalAmount: this.initialTotal,
    })
  },

  methods: {
    clinChangeEvent: function() {
      emitEvent('clin-change', this, {
        id: this._uid,
        obligatedAmount: this.initialObligated,
        totalAmount: this.initialTotal,
      })
    },

    checkFundingValid: function() {
      return this.obligatedAmount <= this.totalAmount
    },

    validateFunding: function() {
      if (this.totalAmount && this.obligatedAmount) {
        this.fundingValid = this.checkFundingValid()
      }
    },

    handleFieldChange: function(event) {
      if (this._uid === event.parent_uid) {
        if (event.name.includes(TOTAL_AMOUNT)) {
          this.totalAmount = parseFloat(event.value)
          this.validateFunding()
        } else if (event.name.includes(OBLIGATED_AMOUNT)) {
          this.obligatedAmount = parseFloat(event.value)
          this.validateFunding()
        } else if (event.name.includes(NUMBER)) {
          this.clinNumber = event.value
        }
      }
    },

    removeClin: function() {
      this.showClin = false
      emitEvent('remove-clin', this, {
        clinIndex: this.clinIndex,
      })
      this.closeModal('remove_clin')
    },
  },

  computed: {
    clinTitle: function() {
      if (!!this.clinNumber) {
        return `CLIN ${this.clinNumber}`
      } else {
        return `CLIN`
      }
    },
    percentObligated: function() {
      const percentage = (this.obligatedAmount / this.totalAmount) * 100
      if (!!percentage) {
        if (percentage > 0 && percentage < 1) {
          return '<1%'
        } else if (percentage > 99 && percentage < 100) {
          return '>99%'
        } else if (percentage > 100) {
          return '>100%'
        } else {
          return `${percentage.toFixed(0)}%`
        }
      } else {
        return '0%'
      }
    },

    removeModalId: function() {
      return `remove-clin-${this.clinIndex}`
    },
  },
}
