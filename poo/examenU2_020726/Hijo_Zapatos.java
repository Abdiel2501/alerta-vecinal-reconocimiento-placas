package examenU2_020726;

public class Hijo_Zapatos extends Padre_Zapato {
    private String tipoCierre;
    private String tipoCostura;
    private boolean suelaCuero;

    public Hijo_Zapatos(String tipo, String color, String calidad, String tipoCierre, String tipoCostura, boolean suelaCuero) {
        super(tipo, color, calidad);
        this.tipoCierre = tipoCierre;
        this.tipoCostura = tipoCostura;
        this.suelaCuero = suelaCuero;
    }

    public String getTipoCierre() {
        return tipoCierre;
    }

    public void setTipoCierre(String tipoCierre) {
        this.tipoCierre = tipoCierre;
    }

    public String getTipoCostura() {
        return tipoCostura;
    }

    public void setTipoCostura(String tipoCostura) {
        this.tipoCostura = tipoCostura;
    }

    public boolean isSuelaCuero() {
        return suelaCuero;
    }

    public void setSuelaCuero(boolean suelaCuero) {
        this.suelaCuero = suelaCuero;
    }

    public void hormarZapato() {
        System.out.println("Colocando el zapato en la horma con costura " + tipoCostura);
    }

    public void bolearZapato() {
        System.out.println("Boleando zapato para darle brillo extremo");
        if (suelaCuero) {
            System.out.println("Aplicando tratamiento especial para suela de cuero");
        }
    }
}
