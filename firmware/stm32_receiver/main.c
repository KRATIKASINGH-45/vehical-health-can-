/* ---------------------------------------------------------------------------
 * Vehicle Health Monitoring System Using CAN  -  RECEIVER NODE
 * Target : STM32F103C8T6 + TJA1050/MCP2551, CAN1 500 kbit/s (same Cube settings as transmitter)
 * Output : 4-digit multiplexed common-cathode 7-segment display
 *            segments a..g -> PB0..PB6 (bit0..bit6), digit selects -> PA4..PA7 (active high via NPN)
 *          buzzer on PB8, red LED on PC13
 * Logic  : mirrors src/receiver_node.py and src/fault_detection.py (thresholds 105 degC / 0.80 g)
 * STATUS : reference firmware - not bench-tested in this submission.
 * ------------------------------------------------------------------------- */
#include "main.h"

#define TEMP_WARN_DC   1050      /* 105.0 degC in 0.1 degC units */
#define VIB_WARN_MG     800      /* 0.800 g                       */

extern CAN_HandleTypeDef hcan;
static const uint8_t SEG[16] = {0x3F,0x06,0x5B,0x4F,0x66,0x6D,0x7D,0x07,0x7F,0x6F,0x77,0x7C,0x39,0x5E,0x79,0x71};
static volatile uint8_t  digits[4] = {0, 0, 0, 0};      /* segment bytes shown on the display */
static volatile uint32_t crc_errors = 0, frames_ok = 0, missing = 0;
static uint8_t last_seq[3]; static uint8_t seen[3];

static uint8_t crc8(const uint8_t *d, uint8_t n) {
    uint8_t c = 0;
    while (n--) { c ^= *d++; for (uint8_t i = 0; i < 8; i++) c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x07) : (uint8_t)(c << 1); }
    return c;
}

static void show_number(uint16_t v) {                    /* 0..999 -> "0v v v" + 'H' marker */
    digits[0] = SEG[(v / 100) % 10]; digits[1] = SEG[(v / 10) % 10]; digits[2] = SEG[v % 10]; digits[3] = 0x76; /* 'H' */
}
static void show_fault(uint16_t code) {                  /* "E101" etc. */
    digits[0] = 0x79; digits[1] = SEG[(code / 100) % 10]; digits[2] = SEG[(code / 10) % 10]; digits[3] = SEG[code % 10];
}

static void handle_frame(uint32_t id, const uint8_t *p) {
    if (id < 0x101 || id > 0x103) return;
    if (crc8(p, 7) != p[7]) { crc_errors++; return; }
    uint8_t n = (uint8_t)(id - 0x101);
    if (seen[n]) missing += (uint8_t)(p[6] - last_seq[n] - 1);
    seen[n] = 1; last_seq[n] = p[6]; frames_ok++;

    int16_t  temp_dc = (int16_t)((p[0] << 8) | p[1]);
    uint16_t vib_mg  = (uint16_t)((p[2] << 8) | p[3]);
    uint8_t hot = temp_dc >= TEMP_WARN_DC, shaky = vib_mg >= VIB_WARN_MG;
    uint16_t code = hot && shaky ? 103 : hot ? 101 : shaky ? 102 : 0;
    if (code) { show_fault(code); HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8, 1); HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, 0); }  /* buzzer on, LED on (active low) */
    else      { show_number((uint16_t)(temp_dc / 10)); HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8, 0); HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, 1); }
}

void HAL_CAN_RxFifo0MsgPendingCallback(CAN_HandleTypeDef *h) {
    CAN_RxHeaderTypeDef rh; uint8_t d[8];
    if (HAL_CAN_GetRxMessage(h, CAN_RX_FIFO0, &rh, d) == HAL_OK && rh.DLC == 8) handle_frame(rh.StdId, d);
}

void HAL_SYSTICK_Callback(void) {                         /* 1 kHz: multiplex one digit per tick */
    static uint8_t k = 0;
    GPIOA->BSRR = 0xF0u << 16;                            /* all digits off (PA4..PA7) */
    GPIOB->ODR = (GPIOB->ODR & ~0x7Fu) | (digits[k] & 0x7Fu);
    GPIOA->BSRR = 1u << (4 + k);
    k = (k + 1) & 3;
}

int main(void) {
    HAL_Init(); SystemClock_Config(); MX_GPIO_Init(); MX_CAN_Init();
    CAN_FilterTypeDef f = {.FilterBank = 0, .FilterMode = CAN_FILTERMODE_IDMASK, .FilterScale = CAN_FILTERSCALE_32BIT,
        .FilterIdHigh = 0x100 << 5, .FilterIdLow = 0, .FilterMaskIdHigh = 0x7FC << 5, .FilterMaskIdLow = 0,  /* accept 0x100-0x103 */
        .FilterFIFOAssignment = CAN_RX_FIFO0, .FilterActivation = ENABLE};
    HAL_CAN_ConfigFilter(&hcan, &f); HAL_CAN_Start(&hcan);
    HAL_CAN_ActivateNotification(&hcan, CAN_IT_RX_FIFO0_MSG_PENDING);
    show_fault(0); for (;;) { __WFI(); }
}
