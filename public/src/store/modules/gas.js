// visualization/src/store/modules/gas.js
const state = {
    currentData: {},
    prediction: {},
    hazardLevel: ''
  }
  
  const getters = {
    currentConcentration: state => state.currentData.currentConcentration || 0,
    hazardLevel: state => state.hazardLevel,
    prediction: state => state.prediction
  }
  
  const mutations = {
    SET_GAS_DATA(state, data) {
      state.currentData = data
    },
    SET_PREDICTION(state, prediction) {
      state.prediction = prediction
    },
    SET_HAZARD_LEVEL(state, level) {
      state.hazardLevel = level
    }
  }
  
  const actions = {
    async fetchGasData({ commit }) {
      // 通过 gasService 获取数据
      const gasService = await import('@/services/gasService.js')
      const data = await gasService.default.getCurrentGasData()
      commit('SET_GAS_DATA', data)
      commit('SET_HAZARD_LEVEL', data.hazardLevel)
      commit('SET_PREDICTION', data.prediction)
    }
  }
  
  export default {
    namespaced: true,
    state,
    getters,
    mutations,
    actions
  }
  