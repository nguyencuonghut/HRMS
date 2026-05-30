// ─── Font: Be Vietnam Pro (weights 300–800) ─────────────────────────────────
import '@fontsource/be-vietnam-pro/300.css'
import '@fontsource/be-vietnam-pro/400.css'
import '@fontsource/be-vietnam-pro/500.css'
import '@fontsource/be-vietnam-pro/600.css'
import '@fontsource/be-vietnam-pro/700.css'
import '@fontsource/be-vietnam-pro/800.css'

import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import { definePreset } from '@primevue/themes'
import Aura from '@primevue/themes/aura'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router'
import { pinia } from '@/stores/pinia'
import '@/assets/styles/main.scss'

// ─── Hồng Hà theme preset (Teal primary) ──────────────────────────────────
const HongHaPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50:  '#f0fdfa',
      100: '#ccfbf1',
      200: '#99f6e4',
      300: '#5eead4',
      400: '#2dd4bf',
      500: '#14b8a6',
      600: '#0d9488',
      700: '#0f766e',
      800: '#115e59',
      900: '#134e4a',
      950: '#042f2e',
    },
    colorScheme: {
      light: {
        primary: {
          color:         '{primary.500}',   // #14b8a6 — vivid teal, matches modal button
          contrastColor: '#ffffff',          // white text
          hoverColor:    '{primary.600}',
          activeColor:   '{primary.700}',
        },
        surface: {
          0:   '#ffffff',
          50:  '{slate.50}',
          100: '{slate.100}',
          200: '{slate.200}',
          300: '{slate.300}',
          400: '{slate.400}',
          500: '{slate.500}',
          600: '{slate.600}',
          700: '{slate.700}',
          800: '{slate.800}',
          900: '{slate.900}',
          950: '{slate.950}',
        },
      },
      dark: {
        primary: {
          color:         '{primary.400}',   // #2dd4bf — bright teal fill (same as Aura default)
          contrastColor: '{surface.900}',   // #18181b — dark text, high contrast
          hoverColor:    '{primary.300}',
          activeColor:   '{primary.200}',
        },
        surface: {
          0:   '#ffffff',
          50:  '{zinc.50}',
          100: '{zinc.100}',
          200: '{zinc.200}',
          300: '{zinc.300}',
          400: '{zinc.400}',
          500: '{zinc.500}',
          600: '{zinc.600}',
          700: '{zinc.700}',
          800: '{zinc.800}',
          900: '{zinc.900}',   // #18181b  ← content.background
          950: '{zinc.950}',   // #09090b  ← formField.background
        },
      },
    },
  },
})

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: HongHaPreset,
    options: {
      prefix: 'p',
      darkModeSelector: '.dark-mode',
      cssLayer: false,
    },
  },
  locale: {
    accept: 'Đồng ý',
    reject: 'Hủy',
    cancel: 'Hủy',
    close: 'Đóng',
    clear: 'Xóa',
    choose: 'Chọn',
    upload: 'Tải lên',
    dayNames: ['Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy'],
    dayNamesShort: ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'],
    dayNamesMin: ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'],
    monthNames: ['Tháng 1','Tháng 2','Tháng 3','Tháng 4','Tháng 5','Tháng 6',
                 'Tháng 7','Tháng 8','Tháng 9','Tháng 10','Tháng 11','Tháng 12'],
    monthNamesShort: ['T1','T2','T3','T4','T5','T6','T7','T8','T9','T10','T11','T12'],
    today: 'Hôm nay',
    firstDayOfWeek: 1,
    dateFormat: 'dd/mm/yy',
    emptyMessage: 'Không có dữ liệu',
    searchMessage: '{0} kết quả',
    selectionMessage: 'Đã chọn {0} mục',
    emptySelectionMessage: 'Chưa chọn',
    emptySearchMessage: 'Không tìm thấy kết quả',
    emptyFilterMessage: 'Không tìm thấy kết quả',
  },
})
app.use(ToastService)
app.use(ConfirmationService)
app.directive('tooltip', Tooltip)

app.mount('#app')
