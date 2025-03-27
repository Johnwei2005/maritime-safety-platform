// visualization/src/store/modules/space.js
const state = {
    spaceData: {}
  }
  
  const getters = {
    spaceData: state => state.spaceData
  }
  
  const mutations = {
    SET_SPACE_DATA(state, data) {
      state.spaceData = data
    }
  }
  
  const actions = {
    async fetchSpaceData({ commit }) {
      // 通过 spaceService 获取数据
      const spaceService = await import('@/services/spaceService.js')
      const data = await spaceService.default.getSpaceData()
      commit('SET_SPACE_DATA', data)
    }
  }
  
  export default {
    namespaced: true,
    state,
    getters,
    mutations,
    actions
  }
  