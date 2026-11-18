; These helpers run only with all HOME mapped; chunk 6 remains HOME here.
                ORG $D800
CACHE_INIT:
                XOR A
                OUT ($F4),A
                LD (CACHE_DIRECT),A
                LD (CACHE_VALID),A
                LD A,1
                LD (CACHE_ENABLE),A
                LD A,2
                LD (CACHE_FF),A
                LD BC,0
                RET
CACHE_VERIFY:
                CALL VALIDATE
                LD BC,1
                RET C
                DEC BC
                RET
CACHE_REMEMBER:
                LD HL,IMAGE
                LD DE,PREVIOUS
                LD BC,80
                LDIR
                LD A,1
                LD (CACHE_VALID),A
                LD BC,0
                RET
CACHE_COMPARE:
                XOR A
                LD (CACHE_DIRECT),A
                LD A,(CACHE_ENABLE)
                OR A
                JR Z,CACHE_COMPARE_DONE
                LD A,(CACHE_VALID)
                OR A
                JR Z,CACHE_COMPARE_DONE
                LD A,(IMAGE+5)
                OR A
                JR Z,CACHE_COMPARE_HEADER
                CP 2
                JR Z,CACHE_COMPARE_HEADER
                CP 7
                JR NZ,CACHE_COMPARE_DONE
CACHE_COMPARE_HEADER:
                LD HL,IMAGE
                LD DE,PREVIOUS
                LD BC,14
                CALL CACHE_MATCH
                JR NZ,CACHE_COMPARE_DONE
                LD HL,PALETTE
                LD DE,PREVIOUS+16
                LD BC,64
                CALL CACHE_MATCH
                JR NZ,CACHE_COMPARE_DONE
                LD A,(IMAGE+5)
                CP 2
                JR NZ,CACHE_COMPARE_CELLS
                LD HL,DF1+6144
                LD DE,$6000
                LD BC,6144
                JR CACHE_COMPARE_ATTRIBUTES
CACHE_COMPARE_CELLS:
                LD HL,DF1+6144
                LD DE,$5800
                LD BC,768
                CALL CACHE_MATCH
                JR NZ,CACHE_COMPARE_DONE
                LD A,(IMAGE+5)
                CP 7
                JR NZ,CACHE_CAN_WIPE
                LD HL,DF1+6912+6144
                LD DE,$7800
                LD BC,768
CACHE_COMPARE_ATTRIBUTES:
                CALL CACHE_MATCH
                JR NZ,CACHE_COMPARE_DONE
CACHE_CAN_WIPE:
                LD A,1
                LD (CACHE_DIRECT),A
CACHE_COMPARE_DONE:
                LD BC,0
                RET
CACHE_STATUS:
                ; BASIC retains its ECM workspace, but loading text uses the
                ; ordinary bitmap and fixed black-on-white native attributes.
                ; No palette or staged image data is needed to see progress.
                DI
                CALL NATIVE
                XOR A
                OUT ($FF),A
                LD (CACHE_FF),A
                LD HL,$5800
                LD DE,$5801
                LD BC,767
                LD (HL),56
                LDIR
                LD A,7
                OUT ($FE),A
                LD BC,0
                EI
                RET
RAM_HELPER_END:
