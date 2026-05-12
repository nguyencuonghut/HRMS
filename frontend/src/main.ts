// ─── Font: Be Vietnam Pro (weights 300–800) ─────────────────────────────────
import '@fontsource/be-vietnam-pro/300.css'
import '@fontsource/be-vietnam-pro/400.css'
import '@fontsource/be-vietnam-pro/500.css'
import '@fontsource/be-vietnam-pro/600.css'
import '@fontsource/be-vietnam-pro/700.css'
import '@fontsource/be-vietnam-pro/800.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { definePreset } from '@primevue/themes'
import Aura from '@primevue/themes/aura'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router'
import '@/assets/styles/main.scss'

// ─── Hồng Hà theme preset (Indigo primary — elegant enterprise) ────────────
const HongHaPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50:  '#eef2ff',
      100: '#e0e7ff',
      200: '#c7d2fe',
      300: '#a5b4fc',
      400: '#818cf8',
      500: '#6366f1',
      600: '#4f46e5',
      700: '#4338ca',
      800: '#3730a3',
      900: '#312e81',
      950: '#1e1b4b',
    },
    colorScheme: {
      light: {
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
        surface: {
          0:   '#ffffff',
          50:  '{zinc.950}',   // #09090b
          100: '{zinc.900}',   // #18181b
          200: '{zinc.800}',   // #27272a
          300: '{zinc.700}',   // #3f3f46
          400: '{zinc.600}',   // #52525b
          500: '{zinc.500}',   // #71717a
          600: '{zinc.400}',   // #a1a1aa
          700: '{zinc.300}',   // #d4d4d8
          800: '{zinc.200}',   // #e4e4e7
          900: '{zinc.100}',   // #f4f4f5
          950: '{zinc.50}',    // #fafafa
        },
      },
    },
  },
})

const app = createApp(App)

app.use(createPinia())
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
