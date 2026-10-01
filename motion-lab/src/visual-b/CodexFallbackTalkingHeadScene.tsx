import { CSSProperties } from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import {
  editorialTalkingHeadDefault,
  type EditorialTalkingHeadContent,
} from "./content";

// AGY did not generate this design: authentication failed. See design/agy/status.md.
// The alternative follows the measured local references and resource-analysis.md.
const colors = {
  ink: "#081224",
  blue: "#2D6BFF",
  gold: "#F5B642",
  white: "#F7F9FC",
  muted: "#A8B4C7",
};
const enter = (frame: number, start: number, duration = 12): CSSProperties => {
  const progress = interpolate(frame, [start, start + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return {
    opacity: progress,
    transform: `translateY(${(1 - progress) * 14}px)`,
  };
};

export type CodexFallbackTalkingHeadSceneProps = {
  content?: EditorialTalkingHeadContent;
};

export const CodexFallbackTalkingHeadScene = ({
  content = editorialTalkingHeadDefault,
}: CodexFallbackTalkingHeadSceneProps) => {
  const frame = useCurrentFrame();
  const underline = interpolate(frame, [21, 43], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill
      style={{
        fontFamily: "JedSans",
        color: colors.white,
        backgroundColor: colors.ink,
      }}
    >
      <Img
        src={staticFile(content.background)}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(90deg, rgba(8,18,36,.99) 0%, rgba(8,18,36,.97) 26%, rgba(8,18,36,.56) 35%, rgba(8,18,36,0) 46%, rgba(8,18,36,0) 73%, rgba(8,18,36,.71) 80%, rgba(8,18,36,.91) 100%)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(8,18,36,.36) 0%, transparent 22%, transparent 80%, rgba(8,18,36,.18) 100%)",
        }}
      />

      <div
        style={{
          position: "absolute",
          left: 84,
          top: 74,
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div style={{ fontSize: 48, fontWeight: 700, letterSpacing: -2 }}>
          Jed
        </div>
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: 10,
            backgroundColor: colors.blue,
            marginTop: 11,
          }}
        />
        <span
          style={{
            fontSize: 19,
            color: colors.muted,
            letterSpacing: 3,
            marginLeft: 15,
          }}
        >
          VISUAL NOTES
        </span>
      </div>
      <div
        style={{
          position: "absolute",
          right: 84,
          top: 92,
          fontSize: 20,
          color: colors.muted,
          letterSpacing: 2,
        }}
      >
        B / 编辑感
      </div>

      <div
        style={{
          position: "absolute",
          left: 84,
          top: 236,
          width: 540,
          ...enter(frame, 0),
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            color: colors.muted,
            fontSize: 24,
            letterSpacing: 2,
          }}
        >
          <span style={{ color: colors.blue, fontWeight: 700 }}>01</span>
          <div style={{ width: 60, height: 2, backgroundColor: colors.blue }} />
          <span>{content.footer}</span>
        </div>
        <div
          style={{
            marginTop: 58,
            fontSize: 60,
            fontWeight: 700,
            letterSpacing: -1.5,
            lineHeight: 1.38,
          }}
        >
          {content.headline.map((line, index) => (
            <div
              key={`${index}-${line}`}
              style={{
                ...enter(frame, 5 + index * 7),
                color:
                  index === content.headline.length - 1
                    ? colors.gold
                    : colors.white,
              }}
            >
              {line}
            </div>
          ))}
        </div>
        <div
          style={{
            marginTop: 29,
            width: 178,
            height: 3,
            backgroundColor: colors.gold,
            transformOrigin: "left",
            transform: `scaleX(${underline})`,
          }}
        />
        <div
          style={{
            marginTop: 25,
            fontSize: 27,
            color: colors.muted,
            lineHeight: 1.7,
            ...enter(frame, 40),
          }}
        >
          {content.eyebrow}
        </div>
      </div>

      <div style={{ position: "absolute", left: 1518, top: 255, width: 312 }}>
        <div
          style={{
            fontSize: 20,
            color: colors.muted,
            letterSpacing: 3,
            paddingBottom: 26,
            borderBottom: "1px solid rgba(168,180,199,.35)",
            ...enter(frame, 18),
          }}
        >
          BUILD THE IDEA
        </div>
        {content.points.map((step, index) => (
          <div
            key={step.title}
            style={{
              paddingTop: 28,
              paddingBottom: 30,
              borderBottom: "1px solid rgba(168,180,199,.25)",
              ...enter(frame, step.cueFrame),
            }}
          >
            <div style={{ display: "flex", gap: 20, alignItems: "baseline" }}>
              <span
                style={{
                  fontSize: 25,
                  color:
                    index === content.points.length - 1
                      ? colors.gold
                      : colors.blue,
                  fontWeight: 700,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                0{index + 1}
              </span>
              <span
                style={{
                  fontSize: step.title.length > 6 ? 32 : 42,
                  fontWeight: 700,
                  lineHeight: 1.45,
                }}
              >
                {step.title}
              </span>
            </div>
            <div
              style={{
                marginLeft: 55,
                marginTop: 13,
                fontSize: 24,
                lineHeight: 1.45,
                color: colors.muted,
              }}
            >
              {step.detail}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          position: "absolute",
          left: 84,
          bottom: 30,
          fontSize: 20,
          color: colors.muted,
          letterSpacing: 1,
        }}
      >
        样式预览 / 非成片
      </div>
    </AbsoluteFill>
  );
};
