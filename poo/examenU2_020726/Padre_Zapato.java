package examenU2_020726;

public class Padre_Zapato {
    private String tipo;
    private String color;
    private String calidad;

    public Padre_Zapato(String tipo, String color, String calidad) {
        this.tipo = tipo;
        this.color = color;
        this.calidad = calidad;
    }

    public String getTipo() {
        return tipo;
    }

    public void setTipo(String tipo) {
        this.tipo = tipo;
    }

    public String getColor() {
        return color;
    }

    public void setColor(String color) {
        this.color = color;
    }

    public String getCalidad() {
        return calidad;
    }

    public void setCalidad(String calidad) {
        this.calidad = calidad;
    }

    public void iniciarProceso() {
        System.out.println("Iniciando fabricacion de " + tipo);
        System.out.println("Color seleccionado " + color);
        if (calidad.equalsIgnoreCase("premium")) {
            System.out.println("Importando material premium de alta calidad");
        } else {
            System.out.println("Utilizando material basico estandar");
        }
    }
}
