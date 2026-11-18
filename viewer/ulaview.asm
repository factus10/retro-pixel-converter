; ULAVIEW: TS2068 + PicoVideo support, assembled with Pasmo --bin.
; MODESET is adapted from Jon Becker's ECMVIEW ecmroutine.asm.
; BASIC reserves $9C00 upward with CLEAR 39935. The complete image is staged
; at $A000..$D64F. $E000..$FFFF is untouched (TS-Pico transfer workspace).
; No executable code is loaded from image files.
                IFDEF RAM_VIEW
                ORG $9B80
                ELSE
                ORG $9C00
                ENDIF
                JP PREPARE
                JP SHOW
                JP EXIT0
                JP HEADER_ENTRY
WIPE_MODE:      DB 0                ; $9C0C / 39948: 0 instant, 1..4 wipes
WIPE_SPEED:     DB 0                ; $9C0D / 39949: delay 0..255
REVEAL_FLAG:    DB 0
WIPE_WIDTH:     DB 32
BLANK_ATTR:     DB 0
BLANK_PIXELS:   DB 0
                JP LEGACY_ECM       ; $9C12 / 39954: synthesize native ECM metadata

IMAGE           EQU $A000
PALETTE         EQU IMAGE+16
DF1             EQU IMAGE+80
CHNG_VID        EQU $0E8E
VIDMOD          EQU $5CC2

; Register writer: D=index, E=value; clobbers A/BC only.
WRITE_REG:
                LD BC,$BF3B
                LD A,D
                OUT (C),A
                LD B,$FF
                LD A,E
                OUT (C),A
                RET

; Disable palette and PicoVideo mode override before ROM display changes.
NATIVE:
                LD D,64
                LD E,0
                CALL WRITE_REG
                INC D
                JP WRITE_REG

; Use the real Timex service to relocate BASIC above both display files.
; Always reserve native ECM first, even for PicoVideo's custom modes.
PREPARE:
                DI
                CALL BLACKOUT
                LD A,2
                CALL MODESET
                DI
                CALL CLEAR_SCREENS
                EI
                RET

; Keep the old display hidden before changing mode, attributes or pixels.
; Do not disable ULA+ while its old bitmap and attributes are still visible.
BLACKOUT:
                LD D,0
                LD E,0
BLACK_LOOP:
                CALL WRITE_REG
                INC D
                LD A,D
                CP 64
                JR NZ,BLACK_LOOP
                LD D,65
                LD E,2
                CALL WRITE_REG
                LD D,64
                LD E,1
                CALL WRITE_REG
                XOR A
                OUT ($FE),A
                RET

; Clear ECM attributes first, then 8x8 attributes, then the remaining bitmap.
; Both INK and PAPER are black during every write, regardless of old palette.
CLEAR_SCREENS:
                LD HL,$6000
                LD DE,$6001
                LD BC,6143
                XOR A
                LD (HL),A
                LDIR
                LD HL,$5800
                LD DE,$5801
                LD BC,767
                LD (HL),A
                LDIR
                LD HL,$7800
                LD DE,$7801
                LD BC,767
                LD (HL),A
                LDIR
                LD HL,$4000
                LD DE,$4001
                LD BC,6143
                LD (HL),A
                LDIR
                RET

; A = ROM native mode; same bank/ROM-switch protocol as ECMVIEW.
MODESET:
                LD (MODE_VALUE),A
                DI
                LD A,1
                OUT ($F4),A
                IN A,($FF)
                SET 7,A
                OUT ($FF),A
                LD A,2
MODE_VALUE      EQU $-1
                PUSH AF
                EI
                CALL CHNG_VID
                DI
                IN A,($FF)
                RES 7,A
                OUT ($FF),A
                XOR A
                OUT ($F4),A
                POP AF
                CP $80
                JR NZ,MODE_DONE
                LD (VIDMOD),A
MODE_DONE:
                EI
                RET

; Return to BASIC after normal completion, BREAK, load error or invalid image.
EXIT0:
                DI
                CALL BLACKOUT
                CALL CLEAR_SCREENS
                CALL NATIVE
                XOR A
                JP MODESET

; Carry set means invalid header/checksum. No display writes on rejection.
CHECK_HEADER:
                LD HL,IMAGE
                LD DE,MAGIC
                LD B,5
                CALL COMPARE
                RET C
                LD A,(IMAGE+7)
                CP 8
                JR NC,INVALID
                LD A,(IMAGE+13)
                OR A
                JR NZ,INVALID
                LD HL,LAYOUTS
                LD B,7
LAYOUT_NEXT:
                PUSH BC
                PUSH HL
                LD DE,IMAGE+5
                LD B,2
                CALL COMPARE
                JR C,LAYOUT_FAIL
                INC DE              ; skip border byte
                LD B,5              ; lengths + palette count
                CALL COMPARE
                JR NC,LAYOUT_OK
LAYOUT_FAIL:
                POP HL
                LD DE,7
                ADD HL,DE
                POP BC
                DJNZ LAYOUT_NEXT
INVALID:
                SCF
                RET
LAYOUT_OK:
                POP HL
                POP BC
                OR A
                RET

; USR $9C09 checks the palette/mode file before loading any screen blocks.
HEADER_ENTRY:
                CALL CHECK_HEADER
                LD BC,1
                RET C
                DEC BC
                RET

VALIDATE:
                CALL CHECK_HEADER
                RET C
                CALL SUM_DATA
                LD HL,(IMAGE+14)
                OR A
                SBC HL,DE
                JR NZ,INVALID
                OR A
                RET
SUM_DATA:
                LD HL,(IMAGE+8)
                LD DE,(IMAGE+10)
                ADD HL,DE
                LD DE,64
                ADD HL,DE
                LD B,H
                LD C,L
                LD HL,PALETTE
                LD DE,0
SUM_LOOP:
                LD A,(HL)
                ADD A,E
                LD E,A
                JR NC,SUM_NO_CARRY
                INC D
SUM_NO_CARRY:
                INC HL
                DEC BC
                LD A,B
                OR C
                JR NZ,SUM_LOOP
                RET

; Old ECM tapes have only ecm-pix and ecm-atr, with native Timex colors.
LEGACY_ECM:
                LD HL,LEGACY_HEADER
                LD DE,IMAGE
                LD BC,16
                LDIR
                XOR A
                LD HL,PALETTE
                LD BC,63
                CALL FILL_BLOCK
                CALL SUM_DATA
                LD (IMAGE+14),DE
                LD BC,0
                RET

; Compare B bytes of (HL) and (DE), advancing both. Carry on mismatch.
COMPARE:
                LD A,(DE)
                CP (HL)
                JR NZ,INVALID
                INC HL
                INC DE
                DJNZ COMPARE
                OR A
                RET

; USR $9C03: BC=0 success, BC=1 invalid. Stack/ROM variables stay in RAM.
SHOW:
                CALL VALIDATE
                LD BC,1
                RET C
                DI
                IFDEF RAM_VIEW
                ; The RAM host sets this only after comparing mode, palette,
                ; border and every attribute byte with the live display.
                LD A,(CACHE_DIRECT)
                OR A
                JR Z,RAM_SHOW_BLACK
                LD A,(WIPE_MODE)
                DEC A
                CP 4
                JR NC,RAM_SHOW_BLACK
                LD A,32
                LD (WIPE_WIDTH),A
                LD A,(IMAGE+5)
                CP 7
                JR NZ,RAM_WIDTH_READY
                LD A,64
                LD (WIPE_WIDTH),A
RAM_WIDTH_READY:
                CALL REVEAL
                LD BC,0
                EI
                RET
RAM_SHOW_BLACK:
                ENDIF
                CALL BLACKOUT
                CALL CLEAR_SCREENS
                XOR A
                LD (REVEAL_FLAG),A
                LD A,32
                LD (WIPE_WIDTH),A
                LD A,(WIPE_MODE)
                DEC A
                CP 4
                JR NC,BULK_COPY
                LD A,(IMAGE+5)
                CP 7
                JR NZ,NOT_WIDE
                LD A,64
                LD (WIPE_WIDTH),A
                JR CHECK_BLACK_PAPER
NOT_WIDE:
                OR A
                JR Z,CHECK_BLACK_PAPER
                CP 2
                JR NZ,BULK_COPY
CHECK_BLACK_PAPER:
                LD A,(IMAGE+6)
                OR A
                JR Z,USE_WIPE
                LD HL,PALETTE
                LD C,0
                LD B,64
FIND_BLACK:
                LD A,(HL)
                OR A
                JR Z,FOUND_BLACK
                INC HL
                INC C
                DJNZ FIND_BLACK
                JR BULK_COPY
FOUND_BLACK:
                LD A,C
                AND $30
                RLCA
                RLCA
                LD E,A
                LD A,C
                AND 7
                BIT 3,C
                JR NZ,BLACK_PAPER
                OR E
                LD (BLANK_ATTR),A
                LD A,255
                JR BLACK_PIXELS_READY
BLACK_PAPER:
                RLCA
                RLCA
                RLCA
                OR E
                LD (BLANK_ATTR),A
                XOR A
BLACK_PIXELS_READY:
                LD (BLANK_PIXELS),A
                CALL FILL_HIDDEN_SCREEN
USE_WIPE:
                LD A,1
                LD (REVEAL_FLAG),A
                JR NO_DF2
BULK_COPY:
                LD HL,DF1
                LD DE,$4000
                LD BC,(IMAGE+8)
                LDIR
                ; HL now points to the staged second display file.
                LD BC,(IMAGE+10)
                LD A,B
                OR C
                JR Z,NO_DF2
                LD DE,$6000
                LDIR
NO_DF2:
                LD A,(IMAGE+6)
                CP 2
                JR Z,QUAD_PALETTE
                OR A
                JR Z,SET_MODE
                LD HL,PALETTE
                LD D,0
ULA_PALETTE:
                LD E,(HL)
                CALL WRITE_REG
                INC HL
                INC D
                LD A,D
                CP 64
                JR NZ,ULA_PALETTE
                JR SET_MODE
QUAD_PALETTE:
                LD D,68
                LD E,0
                CALL WRITE_REG
                LD HL,PALETTE
                LD D,71
                LD E,(HL)
                CALL WRITE_REG
                INC HL
                LD E,(HL)
                CALL WRITE_REG
                INC HL
                LD E,(HL)
                CALL WRITE_REG
                INC HL
                LD E,(HL)
                CALL WRITE_REG
SET_MODE:
                ; The ROM has reserved native ECM and VIDMOD remains 2.
                ; ULA+ modes are selected through PicoVideo register 65, so
                ; leave the physical SCLD in that valid native mode. In
                ; particular, PicoVideo mode 7 is not a native TS2068 mode.
                LD A,(IMAGE+6)
                CP 1
                LD A,2
                JR Z,NATIVE_MODE_READY
                LD A,(IMAGE+5)
NATIVE_MODE_READY:
                OUT ($FF),A
                ; Explicit override works on both old and current PicoVideo:
                ; $80 forces mode 0; other nonzero values force that mode.
                LD A,(IMAGE+5)
                OR A
                JR NZ,OVERRIDE_READY
                LD A,$80
OVERRIDE_READY:
                LD E,A
                LD D,65
                CALL WRITE_REG
                LD A,(IMAGE+6)
                AND 1
                LD E,A
                LD D,64
                CALL WRITE_REG
                LD A,(IMAGE+7)
                OUT ($FE),A
                LD A,(REVEAL_FLAG)
                OR A
                CALL NZ,REVEAL
                LD BC,0
                EI
                RET

; Copy one full-height logical 8-pixel column. C is preserved.
; Hidden columns select a black INK or PAPER slot from the incoming palette.
COPY_COLUMN:
                PUSH BC
                LD A,(IMAGE+5)
                CP 2
                JR Z,ECM_COLUMN
                LD HL,DF1
                LD DE,$4000
                CP 7
                JR NZ,ATTR_COLUMN
                BIT 0,C
                JR Z,WIDE_BANK_READY
                LD HL,DF1+6912
                LD DE,$6000
WIDE_BANK_READY:
                SRL C
ATTR_COLUMN:
                CALL ADD_COLUMN
                PUSH HL
                PUSH DE
                LD BC,6144
                ADD HL,BC
                LD A,D
                ADD A,24
                LD D,A
                LD B,24
                CALL COPY_PLANE
                POP DE
                POP HL
                JR PIXEL_COLUMN
ECM_COLUMN:
                LD HL,DF1+6144
                LD DE,$6000
                CALL ADD_COLUMN
                LD B,192
                CALL COPY_PLANE
                LD HL,DF1
                LD DE,$4000
                CALL ADD_COLUMN
PIXEL_COLUMN:
                LD B,192
                CALL COPY_PLANE
                POP BC
                RET
ADD_COLUMN:
                LD A,L
                ADD A,C
                LD L,A
                LD A,E
                ADD A,C
                LD E,A
                RET
COPY_PLANE:
                LD A,(HL)
                LD (DE),A
                LD A,L
                ADD A,32
                LD L,A
                JR NC,SOURCE_NO_CARRY
                INC H
SOURCE_NO_CARRY:
                LD A,E
                ADD A,32
                LD E,A
                JR NC,DEST_NO_CARRY
                INC D
DEST_NO_CARRY:
                DJNZ COPY_PLANE
                RET
FILL_HIDDEN_SCREEN:
                LD A,(IMAGE+5)
                CP 2
                LD A,(BLANK_ATTR)
                JR NZ,FILL_CELL_ATTRS
                LD HL,$6000
                LD BC,6143
                CALL FILL_BLOCK
                JR FILL_BITMAPS
FILL_CELL_ATTRS:
                LD HL,$5800
                LD BC,767
                CALL FILL_BLOCK
                LD A,(IMAGE+5)
                CP 7
                JR NZ,FILL_BITMAPS
                LD A,(BLANK_ATTR)
                LD HL,$7800
                LD BC,767
                CALL FILL_BLOCK
FILL_BITMAPS:
                LD A,(BLANK_PIXELS)
                LD HL,$4000
                LD BC,6143
                CALL FILL_BLOCK
                LD A,(IMAGE+5)
                CP 7
                RET NZ
                LD A,(BLANK_PIXELS)
                LD HL,$6000
                LD BC,6143
FILL_BLOCK:
                PUSH HL
                POP DE
                INC DE
                LD (HL),A
                LDIR
                RET
WIPE_DELAY:
                LD A,(WIPE_SPEED)
                OR A
                RET Z
                LD B,A
DELAY_OUTER:
                PUSH BC
                LD C,0
DELAY_INNER:
                DEC C
                JR NZ,DELAY_INNER
                POP BC
                DJNZ DELAY_OUTER
                RET
STEP_COLUMN:
                PUSH BC
                CALL COPY_COLUMN
                CALL WIPE_DELAY
                POP BC
                RET
REVEAL:
                LD A,(WIPE_MODE)
                CP 2
                JR Z,REVEAL_RIGHT
                CP 3
                JR Z,REVEAL_CURTAIN
                CP 4
                JR Z,REVEAL_BLINDS
                LD C,0
REVEAL_LEFT_LOOP:
                CALL STEP_COLUMN
                INC C
                LD A,(WIPE_WIDTH)
                CP C
                JR NZ,REVEAL_LEFT_LOOP
                RET
REVEAL_RIGHT:
                LD A,(WIPE_WIDTH)
                DEC A
                LD C,A
REVEAL_RIGHT_LOOP:
                CALL STEP_COLUMN
                DEC C
                LD A,C
                CP 255
                JR NZ,REVEAL_RIGHT_LOOP
                RET
REVEAL_CURTAIN:
                LD A,(WIPE_WIDTH)
                SRL A
                LD B,A
                LD D,A
                DEC A
                LD C,A
CURTAIN_LOOP:
                PUSH BC
                PUSH DE
                CALL COPY_COLUMN
                POP DE
                POP BC
                PUSH BC
                PUSH DE
                LD C,B
                CALL STEP_COLUMN
                POP DE
                POP BC
                DEC C
                INC B
                DEC D
                JR NZ,CURTAIN_LOOP
                RET
REVEAL_BLINDS:
                LD B,0
BLINDS_OUTER:
                LD C,B
BLINDS_INNER:
                CALL STEP_COLUMN
                LD A,C
                ADD A,4
                LD C,A
                LD A,(WIPE_WIDTH)
                CP C
                JR Z,BLINDS_NEXT
                JR NC,BLINDS_INNER
BLINDS_NEXT:
                INC B
                LD A,B
                CP 4
                JR NZ,BLINDS_OUTER
                RET

MAGIC:          DB "ULAV",2
; port, flags, len1(lo/hi), len2(lo/hi), register count.
LAYOUTS:
                DB 0,1,0,27,0,0,64
                DB 2,1,0,24,0,24,64
                DB 6,1,0,24,0,24,64
                DB 7,1,0,27,0,27,64
                DB 7,0,0,27,0,27,0
                DB 3,2,0,24,0,24,4
                DB 2,0,0,24,0,24,0
LEGACY_HEADER:  DB "ULAV",2,2,0,0,0,24,0,24,0,0,0,0
CODE_END:
