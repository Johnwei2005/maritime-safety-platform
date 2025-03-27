// visualization/src/store/index.js
import { createStore } from 'vuex'
import gas from './modules/gas'
import space from './modules/space'

const store = createStore({
  modules: {
    gas,
    space
  }
})

export default store
