; Stock TS-Pico SRAM gateway. Executing code, bounce buffer, state and the
; caller's stack remain HOME. Only chunks 0..3,5,6 may be overlaid.
                ORG $9800
                JP CACHE_STORE       ; 38912
                JP CACHE_LOAD        ; 38915
                JP CACHE_VERIFY      ; 38918
                JP CACHE_PRIME       ; 38921
                JP CACHE_COMPARE     ; 38924
                JP CACHE_REMEMBER    ; 38927
                JP CACHE_INIT        ; 38930
                JP CACHE_STATUS      ; 38933: readable preload palette

CACHE_ADDR      EQU $9B00             ; 0, $4000 or $A000 in selected SRAM region
CACHE_FF        EQU $9B02             ; host's physical FF shadow, DOCK bit clear
CACHE_DIRECT    EQU $9B03
CACHE_VALID     EQU $9B04
CACHE_ENABLE    EQU $9B05
CACHE_OP        EQU $9B06
CACHE_HOME      EQU $9B08
CACHE_EXTERNAL  EQU $9B0A
CACHE_LEFT      EQU $9B0C
CACHE_COUNT     EQU $9B0E
BOUNCE          EQU $9A00
PREVIOUS        EQU $D700
FRAME_BYTES     EQU 13904

CACHE_STORE:
                LD A,1
                JR CACHE_TRANSFER
CACHE_LOAD:
                XOR A
CACHE_TRANSFER:
                DI
                LD (CACHE_OP),A
                XOR A
                OUT ($F4),A
                LD HL,(CACHE_ADDR)
                LD A,L
                OR A
                JP NZ,CACHE_FAIL
                LD A,H
                OR A
                JR Z,CACHE_BASE_OK
                CP $40
                JR Z,CACHE_BASE_OK
                CP $A0
                JP NZ,CACHE_FAIL
CACHE_BASE_OK:
                LD (CACHE_EXTERNAL),HL
                LD HL,$A000
                LD (CACHE_HOME),HL
                LD HL,FRAME_BYTES
                LD (CACHE_LEFT),HL
                LD A,(CACHE_FF)
                AND $7F
                OUT ($FF),A
                ; Low windows do not overlap HOME staging: copy in one LDIR.
                LD A,(CACHE_ADDR+1)
                CP $A0
                JR Z,CACHE_NEXT
                OR A
                LD A,3
                JR Z,CACHE_DIRECT_MASK
                LD A,12
CACHE_DIRECT_MASK:
                OUT ($F4),A
                LD A,(CACHE_OP)
                OR A
                JR Z,CACHE_DIRECT_READ
                LD HL,$A000
                LD DE,(CACHE_ADDR)
                LD BC,FRAME_BYTES
                LDIR
                LD HL,$A000
                LD DE,(CACHE_ADDR)
                LD BC,FRAME_BYTES
                CALL CACHE_MATCH
                JP NZ,CACHE_FAIL
                JP CACHE_OK
CACHE_DIRECT_READ:
                LD HL,(CACHE_ADDR)
                LD DE,$A000
                LD BC,FRAME_BYTES
                LDIR
                JP CACHE_OK
CACHE_NEXT:
                LD HL,(CACHE_LEFT)
                LD A,H
                OR L
                JP Z,CACHE_OK
                LD BC,256
                LD A,H
                OR A
                JR NZ,CACHE_COUNT_OK
                LD C,L
                LD B,0
CACHE_COUNT_OK:
                LD (CACHE_COUNT),BC
                LD A,(CACHE_OP)
                OR A
                JR Z,CACHE_READ
                LD HL,(CACHE_HOME)
                LD DE,BOUNCE
                LDIR
                CALL CACHE_MAP
                LD HL,BOUNCE
                LD DE,(CACHE_EXTERNAL)
                LD BC,(CACHE_COUNT)
                LDIR
                LD HL,BOUNCE
                LD DE,(CACHE_EXTERNAL)
                LD BC,(CACHE_COUNT)
                CALL CACHE_MATCH
                JP NZ,CACHE_FAIL
                JR CACHE_UNMAP
CACHE_READ:
                CALL CACHE_MAP
                LD HL,(CACHE_EXTERNAL)
                LD DE,BOUNCE
                LD BC,(CACHE_COUNT)
                LDIR
                XOR A
                OUT ($F4),A
                LD HL,BOUNCE
                LD DE,(CACHE_HOME)
                LD BC,(CACHE_COUNT)
                LDIR
CACHE_UNMAP:
                XOR A
                OUT ($F4),A
                LD DE,(CACHE_COUNT)
                LD HL,(CACHE_HOME)
                ADD HL,DE
                LD (CACHE_HOME),HL
                LD HL,(CACHE_EXTERNAL)
                ADD HL,DE
                LD (CACHE_EXTERNAL),HL
                LD HL,(CACHE_LEFT)
                OR A
                SBC HL,DE
                LD (CACHE_LEFT),HL
                JP CACHE_NEXT

CACHE_MAP:
                LD A,(CACHE_EXTERNAL+1)
                RLCA
                RLCA
                RLCA
                AND 7
                LD L,A
                LD H,0
                LD DE,CACHE_MASKS
                ADD HL,DE
                LD A,(HL)
                OUT ($F4),A
                RET
CACHE_MASKS:    DB 1,2,4,8,16,32,64,128

; Z=all equal; nonzero flags=mismatch. BC must be nonzero.
CACHE_MATCH:
                LD A,(DE)
                CP (HL)
                RET NZ
                INC HL
                INC DE
                DEC BC
                LD A,B
                OR C
                JR NZ,CACHE_MATCH
                RET

CACHE_PRIME:
                DI
                XOR A
                OUT ($F4),A
                LD A,(CACHE_FF)
                AND $7F
                OUT ($FF),A
                LD A,1
                OUT ($F4),A
                LD B,8
CACHE_PRIME_LOOP:
                LD A,($0000)
                DJNZ CACHE_PRIME_LOOP
CACHE_OK:
                XOR A
                OUT ($F4),A
                LD BC,0
                EI
                RET
CACHE_FAIL:
                XOR A
                OUT ($F4),A
                LD BC,1
                EI
                RET
CACHE_END:
