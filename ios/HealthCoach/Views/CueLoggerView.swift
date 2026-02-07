import SwiftUI

struct CueLoggerView: View {
    let onSubmit: (CueType, String?) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var selectedType: CueType = .stress
    @State private var noteText: String = ""
    @State private var showConfirmation: Bool = false

    var body: some View {
        NavigationStack {
            VStack(spacing: AppSpacing.xxl) {
                // Header
                VStack(spacing: AppSpacing.sm) {
                    Text("How are you feeling?")
                        .font(AppTypography.title2())
                        .foregroundColor(.hcTextPrimary)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility3)
                        .accessibilityAddTraits(.isHeader)

                    Text("Log a cue so your coach can learn your patterns.")
                        .font(AppTypography.subheadline())
                        .foregroundColor(.hcTextSecondary)
                        .multilineTextAlignment(.center)
                        .dynamicTypeSize(...DynamicTypeSize.accessibility2)
                }
                .padding(.top, AppSpacing.lg)

                // Cue Type Picker
                cueTypePicker

                // Note Field
                noteField

                Spacer()

                // Submit Button
                submitButton
            }
            .padding(.horizontal, AppSpacing.xl)
            .background(Color.hcBackground)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title3)
                            .foregroundColor(.hcTextTertiary)
                    }
                    .accessibilityLabel("Cancel")
                    .accessibilityHint("Dismiss the cue logger without saving")
                }
            }
            .toolbarBackground(Color.hcBackground, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }

    // MARK: - Cue Type Picker

    private var cueTypePicker: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Select a cue type")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
                .textCase(.uppercase)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)
                .accessibilityAddTraits(.isHeader)

            LazyVGrid(columns: [
                GridItem(.flexible(), spacing: AppSpacing.md),
                GridItem(.flexible(), spacing: AppSpacing.md)
            ], spacing: AppSpacing.md) {
                ForEach(CueType.allCases) { type in
                    CueTypeButton(
                        type: type,
                        isSelected: selectedType == type
                    ) {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            selectedType = type
                        }
                    }
                }
            }
        }
    }

    // MARK: - Note Field

    private var noteField: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text("Add a note (optional)")
                .font(AppTypography.caption())
                .foregroundColor(.hcTextTertiary)
                .textCase(.uppercase)
                .dynamicTypeSize(...DynamicTypeSize.accessibility1)

            TextField("What triggered this feeling?", text: $noteText, axis: .vertical)
                .font(AppTypography.body())
                .foregroundColor(.hcTextPrimary)
                .lineLimit(2...4)
                .padding(AppSpacing.md)
                .background(Color.hcSurface)
                .clipShape(RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                        .strokeBorder(Color.hcTextTertiary.opacity(0.2), lineWidth: 1)
                )
                .dynamicTypeSize(...DynamicTypeSize.accessibility2)
                .accessibilityLabel("Note field")
                .accessibilityHint("Optionally describe what triggered this feeling")
        }
    }

    // MARK: - Submit Button

    private var submitButton: some View {
        Button {
            onSubmit(selectedType, noteText.isEmpty ? nil : noteText)
            dismiss()
        } label: {
            HStack(spacing: AppSpacing.sm) {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 18, weight: .semibold))
                Text("Log Cue")
                    .font(AppTypography.headline())
            }
            .foregroundColor(.hcBackground)
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppSpacing.lg)
            .background(
                RoundedRectangle(cornerRadius: AppCornerRadius.large, style: .continuous)
                    .fill(Color.hcPrimary)
            )
        }
        .padding(.bottom, AppSpacing.xl)
        .accessibilityLabel("Log cue")
        .accessibilityHint("Submit the \(selectedType.displayName) cue\(noteText.isEmpty ? "" : " with your note")")
    }
}

// MARK: - Cue Type Button

struct CueTypeButton: View {
    let type: CueType
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: AppSpacing.sm) {
                Image(systemName: type.iconName)
                    .font(.system(size: 24, weight: .medium))
                    .foregroundColor(isSelected ? cueColor : .hcTextSecondary)

                Text(type.displayName)
                    .font(AppTypography.callout())
                    .foregroundColor(isSelected ? .hcTextPrimary : .hcTextSecondary)
                    .dynamicTypeSize(...DynamicTypeSize.accessibility1)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppSpacing.lg)
            .background(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                    .fill(isSelected ? cueColor.opacity(0.12) : Color.hcSurface.opacity(0.5))
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium, style: .continuous)
                    .strokeBorder(isSelected ? cueColor.opacity(0.5) : Color.clear, lineWidth: 1.5)
            )
        }
        .buttonStyle(PlainButtonStyle())
        .accessibilityLabel("\(type.displayName) cue type")
        .accessibilityHint(isSelected ? "Currently selected" : "Double tap to select this cue type")
        .accessibilityAddTraits(isSelected ? [.isSelected] : [])
    }

    private var cueColor: Color {
        switch type {
        case .stress: return .hcAlert
        case .pain: return .hcAmber
        case .moodLow: return .hcCalm
        case .moodHigh: return .hcGreen
        case .custom: return .hcPrimary
        }
    }
}

#Preview {
    CueLoggerView { type, note in
        print("Logged: \(type.displayName) - \(note ?? "no note")")
    }
}
