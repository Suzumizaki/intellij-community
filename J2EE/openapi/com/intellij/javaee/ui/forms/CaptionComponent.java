package com.intellij.javaee.ui.forms;

import javax.swing.*;
import java.awt.*;

/**
 * User: Sergey.Vasiliev
 */
public class CaptionComponent extends JPanel {
  private JPanel myRootPanel;
  private JLabel myCaptionLabel;
  private JLabel myDescriptionLabel;
  private JLabel myIconLabel;

  private boolean myBordered = true;

  public CaptionComponent() {
    updateBorder();
    setLayout(new BorderLayout());
    add(myRootPanel, BorderLayout.CENTER);
  }

  public CaptionComponent(String text) {
    this();
    setText(text);  
  }

  private void updateBorder() {
    if (myBordered) {
      myRootPanel.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, Color.LIGHT_GRAY));
    }
    else {
      myRootPanel.setBorder(BorderFactory.createEmptyBorder());
    }
  }

  public void setText(final String text) {
    myCaptionLabel.setText(text);
  }

  public String getText() {
    return myCaptionLabel.getText();
  }

  public void setIcon(final Icon icon) {
    myIconLabel.setIcon(icon);
  }

  public Icon getIcon() {
    return myIconLabel.getIcon();
  }

  public boolean isBordered() {
    return myBordered;
  }
                        

  public String getDescriptionText() {
    return myDescriptionLabel.getText();
  }

  public void setDescriptionText(final String text) {
    myDescriptionLabel.setVisible(text != null && text.trim().length() > 0);

    myDescriptionLabel.setText(text);
  }

  public void setBordered(final boolean bordered) {
    myBordered = bordered;
    updateBorder();
  }
}
